"""HTTP-слой для режима webhook."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import Settings
from app.db import Storage


def create_web_app(
    bot: Bot,
    dp: Dispatcher,
    settings: Settings,
    db: Storage,
) -> web.Application:
    app = web.Application()

    async def healthz(_: web.Request) -> web.Response:
        stats = await db.stats()
        return web.json_response({"status": "ok", "leads": stats["total"]})

    app.router.add_get("/healthz", healthz)

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret.get_secret_value(),
    )
    handler.register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)
    return app
