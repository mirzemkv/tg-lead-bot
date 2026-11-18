"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models import TRANSITIONS, LeadStatus


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Оставить заявку", callback_data="lead:start")
    builder.button(text="💼 Услуги и цены", callback_data="menu:services")
    builder.button(text="📋 Мои заявки", callback_data="menu:my_leads")
    builder.button(text="✍️ Контакты", callback_data="menu:contact")
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Оставить заявку", callback_data="lead:start")
    builder.button(text="⬅️ В меню", callback_data="menu:back")
    builder.adjust(1)
    return builder.as_markup()


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="+7 999 123-45-67",
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="lead:confirm")
    builder.button(text="✏️ Заполнить заново", callback_data="lead:restart")
    builder.button(text="❌ Отмена", callback_data="lead:cancel")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="lead:cancel")]]
    )


def admin_actions(lead_id: int, status: LeadStatus) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    reopened = status in (LeadStatus.DONE, LeadStatus.REJECTED)
    labels = {
        LeadStatus.IN_PROGRESS: "↩️ Вернуть в работу" if reopened else "🔥 Взять в работу",
        LeadStatus.DONE: "✅ Завершить",
        LeadStatus.REJECTED: "❌ Отклонить",
    }
    for target in TRANSITIONS[status]:
        builder.button(
            text=labels[target],
            callback_data=f"adm:status:{lead_id}:{target.value}",
        )
    builder.adjust(2)
    return builder.as_markup()


def leads_navigation(offset: int, limit: int, has_more: bool) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    nav: list[InlineKeyboardButton] = []
    if offset > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Новее",
                callback_data=f"leads:page:{max(offset - limit, 0)}",
            )
        )
    if has_more:
        nav.append(
            InlineKeyboardButton(
                text="Старее ➡️",
                callback_data=f"leads:page:{offset + limit}",
            )
        )
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
