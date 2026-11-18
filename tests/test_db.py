"""Тесты хранилища: заявки, статусы, статистика, CSV."""

from __future__ import annotations

import csv

import pytest

from app.db import Storage
from app.models import LeadStatus


@pytest.fixture
async def db(tmp_path):
    storage = Storage(tmp_path / "test.sqlite3")
    await storage.connect()
    yield storage
    await storage.close()


async def _make_lead(db: Storage, user_id: int = 1):
    await db.upsert_user(user_id, "tester", "Иван")
    return await db.create_lead(
        user_id=user_id,
        username="tester",
        name="Иван",
        phone="+7 (999) 123-45-67",
        task="Нужен телеграм-бот для приёма заявок",
    )


async def test_create_lead(db: Storage):
    lead = await _make_lead(db)
    assert lead.id == 1
    assert lead.status is LeadStatus.NEW
    assert lead.phone == "+7 (999) 123-45-67"


async def test_status_transitions(db: Storage):
    lead = await _make_lead(db)

    updated = await db.set_status(lead.id, LeadStatus.IN_PROGRESS)
    assert updated is not None
    assert updated.status is LeadStatus.IN_PROGRESS

    done = await db.set_status(lead.id, LeadStatus.DONE)
    assert done is not None
    assert done.status is LeadStatus.DONE


async def test_missing_lead(db: Storage):
    assert await db.get_lead(999) is None


async def test_user_leads_and_limit(db: Storage):
    await _make_lead(db)
    await _make_lead(db)

    leads = await db.user_leads(user_id=1)
    assert [lead.id for lead in leads] == [2, 1]
    assert await db.count_recent_leads(1) == 2


async def test_list_leads_pagination(db: Storage):
    for _ in range(7):
        await _make_lead(db)

    page, has_more = await db.list_leads(offset=0, limit=5)
    assert len(page) == 5
    assert has_more is True

    page, has_more = await db.list_leads(offset=5, limit=5)
    assert len(page) == 2
    assert has_more is False


async def test_stats(db: Storage):
    first = await _make_lead(db)
    await _make_lead(db)
    await db.set_status(first.id, LeadStatus.DONE)

    stats = await db.stats()
    assert stats["total"] == 2
    assert stats["new"] == 1
    assert stats["done"] == 1
    assert stats["today"] == 2


async def test_export_csv(db: Storage, tmp_path):
    await _make_lead(db)
    path = await db.export_csv(tmp_path / "leads.csv")

    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file, delimiter=";"))

    assert rows[0][0] == "ID"
    assert len(rows) == 2
    assert rows[1][2] == "Иван"
