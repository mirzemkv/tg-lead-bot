"""Хранилище заявок на SQLite.

Одно соединение на процесс, запись под замком. Для демо и небольшого
бизнеса этого достаточно: SQLite держит тысячи заявок без проблем.
"""

from __future__ import annotations

import asyncio
import csv
import io
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from app.models import Lead, LeadStatus

MSK = timezone(timedelta(hours=3))

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    username   TEXT,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL,
    task       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);

CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_user ON leads (user_id);
"""


def utcnow() -> datetime:
    return datetime.now(UTC)


def _day_start(days_ago: int = 0) -> datetime:
    now = datetime.now(MSK)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return (start - timedelta(days=days_ago)).astimezone(UTC)


def _to_lead(row: aiosqlite.Row) -> Lead:
    return Lead(
        id=row["id"],
        user_id=row["user_id"],
        username=row["username"],
        name=row["name"],
        phone=row["phone"],
        task=row["task"],
        status=LeadStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class Storage:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Storage is not connected")
        return self._conn

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        await self.conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name, utcnow().isoformat()),
        )
        await self.conn.commit()

    async def create_lead(
        self,
        *,
        user_id: int,
        username: str | None,
        name: str,
        phone: str,
        task: str,
    ) -> Lead:
        now = utcnow().isoformat()
        async with self._lock:
            cursor = await self.conn.execute(
                """
                INSERT INTO leads
                    (user_id, username, name, phone, task, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, name, phone, task, LeadStatus.NEW.value, now, now),
            )
            await self.conn.commit()
            lead_id = cursor.lastrowid

        lead = await self.get_lead(int(lead_id))
        if lead is None:  # pragma: no cover - защита от гонки
            raise RuntimeError(f"Lead {lead_id} not found after insert")
        return lead

    async def get_lead(self, lead_id: int) -> Lead | None:
        async with self.conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)) as cursor:
            row = await cursor.fetchone()
        return _to_lead(row) if row else None

    async def set_status(self, lead_id: int, status: LeadStatus) -> Lead | None:
        async with self._lock:
            await self.conn.execute(
                "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, utcnow().isoformat(), lead_id),
            )
            await self.conn.commit()
        return await self.get_lead(lead_id)

    async def user_leads(self, user_id: int, limit: int = 5) -> list[Lead]:
        async with self.conn.execute(
            "SELECT * FROM leads WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [_to_lead(row) for row in rows]

    async def count_recent_leads(self, user_id: int, hours: int = 24) -> int:
        since = (utcnow() - timedelta(hours=hours)).isoformat()
        async with self.conn.execute(
            "SELECT COUNT(*) FROM leads WHERE user_id = ? AND created_at >= ?",
            (user_id, since),
        ) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row else 0

    async def list_leads(
        self,
        status: LeadStatus | None = None,
        offset: int = 0,
        limit: int = 5,
    ) -> tuple[list[Lead], bool]:
        sql = "SELECT * FROM leads"
        params: list[object] = []
        if status is not None:
            sql += " WHERE status = ?"
            params.append(status.value)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit + 1, offset])

        async with self.conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        leads = [_to_lead(row) for row in rows[:limit]]
        return leads, len(rows) > limit

    async def stats(self) -> dict[str, int]:
        async with self.conn.execute(
            "SELECT status, COUNT(*) FROM leads GROUP BY status"
        ) as cursor:
            by_status = {row[0]: int(row[1]) for row in await cursor.fetchall()}

        async with self.conn.execute(
            "SELECT COUNT(*) FROM leads WHERE created_at >= ?", (_day_start().isoformat(),)
        ) as cursor:
            today = int((await cursor.fetchone())[0])

        async with self.conn.execute(
            "SELECT COUNT(*) FROM leads WHERE created_at >= ?",
            (_day_start(days_ago=6).isoformat(),),
        ) as cursor:
            week = int((await cursor.fetchone())[0])

        return {
            "total": sum(by_status.values()),
            "new": by_status.get(LeadStatus.NEW.value, 0),
            "in_progress": by_status.get(LeadStatus.IN_PROGRESS.value, 0),
            "done": by_status.get(LeadStatus.DONE.value, 0),
            "rejected": by_status.get(LeadStatus.REJECTED.value, 0),
            "today": today,
            "week": week,
        }

    async def export_csv(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        async with self.conn.execute("SELECT * FROM leads ORDER BY id") as cursor:
            rows = await cursor.fetchall()

        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(["ID", "Дата", "Имя", "Телефон", "Telegram", "Статус", "Задача"])
        for row in rows:
            created = datetime.fromisoformat(row["created_at"]).astimezone(MSK)
            writer.writerow(
                [
                    row["id"],
                    created.strftime("%d.%m.%Y %H:%M"),
                    row["name"],
                    row["phone"],
                    f"@{row['username']}" if row["username"] else "",
                    LeadStatus(row["status"]).label,
                    row["task"],
                ]
            )

        await asyncio.to_thread(
            target.write_text,
            buffer.getvalue(),
            encoding="utf-8-sig",
            newline="",
        )
        return target
