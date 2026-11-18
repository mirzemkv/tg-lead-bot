"""Middleware: защита от двойных нажатий и флуда."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Не чаще одного события в `rate` секунд на пользователя."""

    def __init__(self, rate: float = 0.7) -> None:
        self.rate = rate
        self._last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)

        now = time.monotonic()
        if now - self._last.get(user.id, 0.0) < self.rate:
            if isinstance(event, CallbackQuery):
                await event.answer("Секунду 🙂")
            return None

        self._last[user.id] = now
        return await handler(event, data)
