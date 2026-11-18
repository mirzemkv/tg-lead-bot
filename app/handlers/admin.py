"""Админ-панель: заявки, статусы, статистика, выгрузка."""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from app import content
from app.db import MSK, Storage
from app.filters import IsAdmin
from app.keyboards import admin_actions, leads_navigation
from app.models import TRANSITIONS, LeadStatus

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PAGE_SIZE = 5


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer(content.ADMIN_HELP)


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Storage) -> None:
    data = await db.stats()
    await message.answer(content.stats(data))


@router.message(Command("leads"))
async def cmd_leads(message: Message, db: Storage) -> None:
    leads, has_more = await db.list_leads(offset=0, limit=PAGE_SIZE)
    await message.answer(
        content.lead_list(leads),
        reply_markup=leads_navigation(0, PAGE_SIZE, has_more),
    )


@router.callback_query(F.data.startswith("leads:page:"))
async def page_leads(call: CallbackQuery, db: Storage) -> None:
    try:
        offset = max(int(call.data.rsplit(":", 1)[1]), 0)
    except (ValueError, IndexError):
        await call.answer("Некорректная страница", show_alert=True)
        return

    leads, has_more = await db.list_leads(offset=offset, limit=PAGE_SIZE)
    await call.answer()
    if call.message is not None:
        try:
            await call.message.edit_text(
                content.lead_list(leads),
                reply_markup=leads_navigation(offset, PAGE_SIZE, has_more),
            )
        except TelegramBadRequest:
            logger.debug("Список заявок не изменился")


@router.message(Command("export"))
async def cmd_export(message: Message, db: Storage) -> None:
    stamp = datetime.now(MSK).strftime("%Y%m%d_%H%M")
    path = await db.export_csv(f"exports/leads_{stamp}.csv")
    await message.answer_document(
        FSInputFile(path, filename=f"leads_{stamp}.csv"),
        caption="Все заявки в CSV. Открывается в Excel и Google Sheets.",
    )


@router.callback_query(F.data.startswith("adm:status:"))
async def change_status(call: CallbackQuery, db: Storage, bot: Bot) -> None:
    parts = (call.data or "").split(":")
    if len(parts) != 4:
        await call.answer("Некорректная команда", show_alert=True)
        return

    try:
        lead_id = int(parts[2])
        target = LeadStatus(parts[3])
    except ValueError:
        await call.answer("Некорректный статус", show_alert=True)
        return

    lead = await db.get_lead(lead_id)
    if lead is None:
        await call.answer("Заявка не найдена", show_alert=True)
        return

    if target not in TRANSITIONS[lead.status]:
        await call.answer("Этот переход недоступен", show_alert=True)
        return

    updated = await db.set_status(lead_id, target)
    if updated is None:  # pragma: no cover - защита от гонки
        await call.answer("Не удалось обновить заявку", show_alert=True)
        return

    await call.answer(f"Статус: {target.label}")
    if call.message is not None:
        try:
            await call.message.edit_text(
                content.admin_card(updated),
                reply_markup=admin_actions(updated.id, updated.status),
            )
        except TelegramBadRequest:
            logger.debug("Карточка заявки #%s не изменилась", lead_id)

    try:
        await bot.send_message(updated.user_id, content.notify_user_status(updated))
    except (TelegramForbiddenError, TelegramBadRequest):
        logger.info("Клиент %s недоступен для уведомления", updated.user_id)
