"""Настройки приложения.

Значения читаются из переменных окружения или из файла `.env`.
Секреты хранятся в SecretStr и не попадают в логи.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: SecretStr
    admin_ids: str = ""

    # Хранилище
    db_path: Path = Path("data/leadbot.sqlite3")

    # Режим работы: пустой webhook_base_url включает long polling
    webhook_base_url: str = ""
    webhook_secret: SecretStr = SecretStr("change-me")
    port: int = 8080

    # Необязательная интеграция с Google Sheets через Apps Script
    sheets_webhook_url: str = ""

    # Локальный прокси для разработки (на хостинге обычно не нужен)
    proxy_url: str = ""

    # Поведение
    log_level: str = "INFO"
    rate_limit_seconds: float = 0.7
    daily_lead_limit: int = 3
    support_contact: str = "@leadflow_support"

    @field_validator("webhook_base_url", mode="before")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        """Пустое значение означает polling.

        На Render переменная RENDER_EXTERNAL_URL подставляется автоматически,
        поэтому webhook включается без ручной настройки.
        """
        url = str(value or "").strip().rstrip("/")
        if not url:
            url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url

    @property
    def admins(self) -> tuple[int, ...]:
        """ID администраторов из строки вида `123456789,987654321`."""
        parts = re.split(r"[,;\s]+", self.admin_ids)
        return tuple(int(part) for part in parts if part.strip())

    @property
    def webhook_path(self) -> str:
        return f"/webhook/{self.webhook_secret.get_secret_value()}"

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url}{self.webhook_path}"
