"""Сценарий приёма заявки: имя, телефон, задача, подтверждение."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app import content
from app.config import Settings
from app.db import Storage
from app.keyboards import cancel_keyboard, confirm_keyboard, main_menu, phone_keyboard
from app.services.notify import notify_admins
from app.services.sheets import export_lead
from app.validators import clean_text, is_valid_name, is_valid_task, normalize_phone

logger = logging.getLogger(__name__)

router = Router(name="leads")


class LeadForm(StatesGroup):
    name = State()
    phone = State()
    task = State()
    confirm = State()


async def _cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(content.CANCELLED, reply_markup=ReplyKeyboardRemove())
    await message.answer("Чем помочь?", reply_markup=main_menu())


@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await _cancel(message, state)


@router.callback_query(F.data == "lead:cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer("Отменено")
    if call.message is not None:
        await call.message.edit_reply_markup(reply_markup=None)
        await _cancel(call.message, state)


@router.callback_query(F.data == "lead:start")
async def start_lead(
    call: CallbackQuery,
    state: FSMContext,
    db: Storage,
    settings: Settings,
) -> None:
    recent = await db.count_recent_leads(call.from_user.id, hours=24)
    if recent >= settings.daily_lead_limit:
        await call.answer(
            "На сегодня лимит заявок исчерпан. Напишите администратору напрямую.",
            show_alert=True,
        )
        return

    await db.upsert_user(call.from_user.id, call.from_user.username, call.from_user.first_name)
    await state.clear()
    await state.set_state(LeadForm.name)
    await call.answer()

    if call.message is not None:
        await call.message.answer(content.ASK_NAME, reply_markup=cancel_keyboard())


@router.message(LeadForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    if not is_valid_name(message.text):
        await message.answer(content.BAD_NAME, reply_markup=cancel_keyboard())
        return

    await state.update_data(name=clean_text(message.text))
    await state.set_state(LeadForm.phone)
    await message.answer(content.ASK_PHONE, reply_markup=phone_keyboard())


@router.message(LeadForm.phone, F.text == "Отмена")
async def phone_cancel(message: Message, state: FSMContext) -> None:
    await _cancel(message, state)


@router.message(LeadForm.phone, F.contact)
async def process_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if contact is None:
        return

    if contact.user_id is not None and contact.user_id != message.from_user.id:
        await message.answer(
            "Это чужой контакт. Отправьте свой номер кнопкой ниже.",
            reply_markup=phone_keyboard(),
        )
        return

    phone = normalize_phone(contact.phone_number)
    if phone is None:
        await message.answer(content.BAD_PHONE, reply_markup=phone_keyboard())
        return

    await _save_phone(message, state, phone)


@router.message(LeadForm.phone, F.text)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text)
    if phone is None:
        await message.answer(content.BAD_PHONE, reply_markup=phone_keyboard())
        return

    await _save_phone(message, state, phone)


async def _save_phone(message: Message, state: FSMContext, phone: str) -> None:
    await state.update_data(phone=phone)
    await state.set_state(LeadForm.task)
    await message.answer(content.ASK_TASK, reply_markup=ReplyKeyboardRemove())


@router.message(LeadForm.task, F.text == "Отмена")
async def task_cancel(message: Message, state: FSMContext) -> None:
    await _cancel(message, state)


@router.message(LeadForm.task, F.text)
async def process_task(message: Message, state: FSMContext) -> None:
    if not is_valid_task(message.text):
        await message.answer(content.BAD_TASK, reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    task = clean_text(message.text)
    await state.update_data(task=task)
    await state.set_state(LeadForm.confirm)

    await message.answer(
        content.confirm(data["name"], data["phone"], task),
        reply_markup=confirm_keyboard(),
    )


@router.callback_query(LeadForm.confirm, F.data == "lead:restart")
async def restart_lead(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_data({})
    await state.set_state(LeadForm.name)
    await call.answer()
    if call.message is not None:
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(content.ASK_NAME, reply_markup=cancel_keyboard())


@router.callback_query(LeadForm.confirm, F.data == "lead:confirm")
async def submit_lead(
    call: CallbackQuery,
    state: FSMContext,
    db: Storage,
    settings: Settings,
    bot: Bot,
) -> None:
    data = await state.get_data()
    name, phone, task = data.get("name"), data.get("phone"), data.get("task")

    if not (name and phone and task):
        await state.clear()
        await call.answer("Форма устарела. Начнём заново.", show_alert=True)
        return

    lead = await db.create_lead(
        user_id=call.from_user.id,
        username=call.from_user.username,
        name=name,
        phone=phone,
        task=task,
    )
    await state.clear()
    await call.answer("Заявка отправлена")

    if call.message is not None:
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.answer(content.lead_created(lead), reply_markup=main_menu())

    await notify_admins(bot, settings.admins, lead)
    await export_lead(settings, lead)

    logger.info("Новая заявка #%s от %s", lead.id, lead.user_id)


@router.callback_query(F.data.in_({"lead:confirm", "lead:restart"}))
async def stale_form(call: CallbackQuery) -> None:
    await call.answer("Форма уже неактивна. Откройте меню и начните заново.", show_alert=True)
