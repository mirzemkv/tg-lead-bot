"""Проверка и нормализация пользовательского ввода."""

from __future__ import annotations

import re

_PHONE_ALLOWED = re.compile(r"^[\d\s()+\-]{7,25}$")
_URL = re.compile(r"https?://|www\.|t\.me/", re.IGNORECASE)
_LETTER = re.compile(r"[A-Za-zА-Яа-яЁё]")


def normalize_phone(raw: str | None) -> str | None:
    """Приводит номер к виду `+7 (999) 123-45-67`.

    Понимает российские форматы (10 цифр, 8..., +7...) и международные
    номера длиной до 15 цифр. Возвращает None, если номер не похож на телефон.
    """
    if not raw:
        return None

    value = raw.strip()
    if not _PHONE_ALLOWED.match(value):
        return None

    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]

    if len(digits) == 10:
        return f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}"

    if 11 <= len(digits) <= 15:
        return f"+{digits}"

    return None


def phone_digits(phone: str) -> str:
    """Только цифры: удобно для ссылки `tel:` и поиска дублей."""
    return re.sub(r"\D", "", phone)


def is_valid_name(raw: str | None) -> bool:
    if not raw:
        return False
    value = " ".join(raw.split())
    return 2 <= len(value) <= 64 and bool(_LETTER.search(value)) and not _URL.search(value)


def is_valid_task(raw: str | None) -> bool:
    if not raw:
        return False
    value = raw.strip()
    return 10 <= len(value) <= 1000 and bool(_LETTER.search(value))


def clean_text(raw: str | None) -> str:
    return " ".join((raw or "").split())
