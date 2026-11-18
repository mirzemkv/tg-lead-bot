"""Проверки телефона, имени и описания задачи."""

from app.validators import is_valid_name, is_valid_task, normalize_phone, phone_digits


def test_normalize_phone_russian_formats():
    assert normalize_phone("8 (999) 123-45-67") == "+7 (999) 123-45-67"
    assert normalize_phone("+7 999 123 45 67") == "+7 (999) 123-45-67"
    assert normalize_phone("9991234567") == "+7 (999) 123-45-67"
    assert normalize_phone("79991234567") == "+7 (999) 123-45-67"


def test_normalize_phone_rejects_garbage():
    assert normalize_phone("") is None
    assert normalize_phone(None) is None
    assert normalize_phone("123") is None
    assert normalize_phone("позвоните мне") is None


def test_normalize_phone_international():
    assert normalize_phone("+1 202 555 0143") == "+12025550143"


def test_phone_digits():
    assert phone_digits("+7 (999) 123-45-67") == "79991234567"


def test_is_valid_name():
    assert is_valid_name("Иван")
    assert is_valid_name("  Мария  ")
    assert not is_valid_name("A")
    assert not is_valid_name("https://example.com")
    assert not is_valid_name("12345")


def test_is_valid_task():
    assert is_valid_task("Нужен бот для приёма заявок")
    assert not is_valid_task("мало")
    assert not is_valid_task("")
