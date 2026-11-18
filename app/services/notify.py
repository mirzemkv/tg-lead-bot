"""Уведомления администраторов."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app import content
from app.keyboards import admin_actions
from app.models import Lead

logger = logging.getLogger(__name__)


async def notify_admins(bot: Bot, admin_ids: tuple[int, ...], lead: Lead) -> None:
    if not admin_ids:
        logger.warning("ADMIN_IDS пуст: заявка #%s сохранена, но никому не отправлена", lead.id)
        return

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                admin_id,
                content.admin_card(lead),
                reply_markup=admin_actions(lead.id, lead.status),
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            logger.warning(
                "Не удалось отправить заявку #%s админу %s",
                lead.id,
                admin_id,
                exc_info=True,
            )
