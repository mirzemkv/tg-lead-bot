"""Экспорт заявки в Google Sheets через Apps Script.

Интеграция необязательная: если `SHEETS_WEBHOOK_URL` пуст, бот работает
как обычно. Ошибки внешнего сервиса не должны ломать приём заявок.
"""

from __future__ import annotations

import logging

import aiohttp

from app.config import Settings
from app.models import Lead

logger = logging.getLogger(__name__)


async def export_lead(settings: Settings, lead: Lead) -> None:
    url = settings.sheets_webhook_url
    if not url:
        return

    payload = {
        "id": lead.id,
        "created_at": lead.created_at.isoformat(),
        "name": lead.name,
        "phone": lead.phone,
        "username": lead.username or "",
        "task": lead.task,
        "status": lead.status.value,
    }

    timeout = aiohttp.ClientTimeout(total=6)
    try:
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(url, json=payload) as response,
        ):
            if response.status >= 300:
                logger.warning("Sheets webhook вернул %s", response.status)
    except (aiohttp.ClientError, TimeoutError):
        logger.warning(
            "Sheets webhook недоступен, заявка #%s осталась в базе",
            lead.id,
            exc_info=True,
        )
