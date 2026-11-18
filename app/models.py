"""Доменные модели заявки."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    REJECTED = "rejected"

    @property
    def label(self) -> str:
        return STATUS_LABELS[self]


STATUS_LABELS: dict[LeadStatus, str] = {
    LeadStatus.NEW: "🆕 Новая",
    LeadStatus.IN_PROGRESS: "🛠 В работе",
    LeadStatus.DONE: "✅ Выполнена",
    LeadStatus.REJECTED: "❌ Отклонена",
}

# Разрешённые переходы между статусами
TRANSITIONS: dict[LeadStatus, tuple[LeadStatus, ...]] = {
    LeadStatus.NEW: (LeadStatus.IN_PROGRESS, LeadStatus.REJECTED),
    LeadStatus.IN_PROGRESS: (LeadStatus.DONE, LeadStatus.REJECTED),
    LeadStatus.DONE: (LeadStatus.IN_PROGRESS,),
    LeadStatus.REJECTED: (LeadStatus.IN_PROGRESS,),
}


@dataclass(slots=True, frozen=True)
class Lead:
    id: int
    user_id: int
    username: str | None
    name: str
    phone: str
    task: str
    status: LeadStatus
    created_at: datetime
    updated_at: datetime
