"""Общие обработчики: меню, справка, история заявок."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import CallbackQuery, Message

from app import content
from app.config import Settings
from app.db import Storage
from app.keyboards import back_to_menu, main_menu

router = Router(name="common")


@router.message(Command("start", "menu", "help"))
async def cmd_start(message: Message, db: Storage, settings: Settings) -> None:
    if message.from_user is not None:
        await db.upsert_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )

    text = content.START
    if message.from_user is not None and message.from_user.id in settings.admins:
        text += "\n\n<i>Вы администратор: команды в /admin.</i>"

    await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "menu:back")
async def menu_back(call: CallbackQuery) -> None:
    await call.answer()
    if call.message is not None:
        await call.message.edit_text(content.START, reply_markup=main_menu())


@router.callback_query(F.data == "menu:services")
async def menu_services(call: CallbackQuery) -> None:
    await call.answer()
    if call.message is not None:
        await call.message.edit_text(content.SERVICES, reply_markup=back_to_menu())


@router.callback_query(F.data == "menu:contact")
async def menu_contact(call: CallbackQuery) -> None:
    await call.answer()
    if call.message is not None:
        await call.message.edit_text(content.CONTACT, reply_markup=back_to_menu())


@router.callback_query(F.data == "menu:my_leads")
async def menu_my_leads(call: CallbackQuery, db: Storage) -> None:
    await call.answer()
    leads = await db.user_leads(call.from_user.id, limit=5)
    if call.message is not None:
        await call.message.edit_text(content.my_leads(leads), reply_markup=back_to_menu())


@router.message(StateFilter(None), F.text)
async def fallback(message: Message) -> None:
    await message.answer("Не понял команду. Вот что я умею:", reply_markup=main_menu())
