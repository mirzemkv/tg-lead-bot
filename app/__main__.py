"""Точка входа: long polling локально, webhook на хостинге."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from app import __version__
from app.config import Settings
from app.db import Storage
from app.handlers import admin, common, leads
from app.middlewares import ThrottlingMiddleware
from app.web import create_web_app

logger = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def build_dispatcher(settings: Settings, db: Storage) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage(), settings=settings, db=db)

    throttle = ThrottlingMiddleware(settings.rate_limit_seconds)
    dp.message.middleware(throttle)
    dp.callback_query.middleware(throttle)

    dp.include_router(admin.router)
    dp.include_router(leads.router)
    dp.include_router(common.router)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> bool:
        logger.error("Ошибка обработки апдейта: %s", event.exception, exc_info=event.exception)
        return True

    return dp


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Режим: long polling")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def run_webhook(bot: Bot, dp: Dispatcher, settings: Settings, db: Storage) -> None:
    from aiohttp import web

    app = create_web_app(bot, dp, settings, db)

    @dp.startup()
    async def set_webhook() -> None:
        await bot.set_webhook(
            settings.webhook_url,
            secret_token=settings.webhook_secret.get_secret_value(),
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=False,
        )
        logger.info("Webhook установлен: %s", settings.webhook_url)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.port)
    await site.start()
    logger.info("Режим: webhook, порт %s", settings.port)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    settings = Settings()
    setup_logging(settings.log_level)
    logger.info("LeadFlow %s", __version__)

    if not settings.admins:
        logger.warning("ADMIN_IDS не задан: заявки будут сохраняться без уведомлений")

    db = Storage(settings.db_path)
    await db.connect()

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        session=AiohttpSession(proxy=settings.proxy_url or None),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher(settings, db)

    try:
        if settings.webhook_base_url:
            if settings.webhook_secret.get_secret_value() == "change-me":
                logger.warning("WEBHOOK_SECRET оставлен по умолчанию, смените его")
            await run_webhook(bot, dp, settings, db)
        else:
            await run_polling(bot, dp)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
