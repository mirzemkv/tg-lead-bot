"""Тексты интерфейса. Один файл, чтобы правки не искать по коду."""

from __future__ import annotations

from html import escape

from app.db import MSK
from app.models import Lead, LeadStatus

START = """<b>LeadFlow</b>: приём заявок для небольшого бизнеса.

Клиент отвечает на три вопроса, а заявка сразу приходит вам в Telegram:
имя, телефон, задача. Без потерянных сообщений и таблиц в блокноте.

<b>Что внутри демо</b>
• заявка за 40 секунд
• уведомление и статусы для администратора
• история заявок и статистика
• выгрузка в CSV

Выберите действие ниже."""

SERVICES = """<b>Услуги и сроки</b>

<b>Telegram-бот приёма заявок</b>
Заявки в Telegram плюс таблица или CRM. От 12 000 ₽, 3 дня.

<b>Парсер сайта</b>
Сбор данных и выгрузка в Excel или Google Sheets. От 5 000 ₽, 2 дня.

<b>Срочная починка</b>
Бот не отвечает, парсер сломался, отвалился API. От 2 500 ₽, 1 день.

<b>Поддержка</b>
Обновления, доработки, мониторинг. От 3 000 ₽ в месяц.

<i>Сначала ТЗ и фиксированная смета, потом работа.</i>"""

CONTACT = """<b>На связи</b>

Меня зовут Андрей. Я инженер ОИЯИ (проект NICA) и Python-разработчик: боты, парсеры, интеграции.

GitHub: https://github.com/mirzemkv

Обычно отвечаю в течение рабочего дня.
Если задача срочная, оставьте заявку и напишите «срочно» в описании."""

NO_LEADS = """Заявок пока нет.

Нажмите «Оставить заявку»: это займёт меньше минуты."""

ASK_NAME = """<b>Шаг 1 из 3</b>

Как вас зовут? Напишите имя, чтобы я знал, к кому обращаться."""

ASK_PHONE = """<b>Шаг 2 из 3</b>

Оставьте номер телефона: кнопкой ниже или текстом в формате +7 999 123-45-67."""

ASK_TASK = """<b>Шаг 3 из 3</b>

Опишите задачу в двух-трёх предложениях: что нужно сделать и в какой срок.

Например: «Нужен бот, который принимает заявки с сайта и присылает их в Telegram»."""

BAD_NAME = "Имя должно быть от 2 до 64 символов, без ссылок. Попробуйте ещё раз."

BAD_PHONE = "Не похоже на телефон. Отправьте номер в формате +7 999 123-45-67 или кнопкой ниже."

BAD_TASK = "Описание должно быть от 10 до 1000 символов. Добавьте пару деталей о задаче."

CANCELLED = "Хорошо, отменил. Если передумаете, я рядом."

ADMIN_ONLY = "Команда доступна только администратору."


def confirm(lead_name: str, phone: str, task: str) -> str:
    return f"""<b>Проверьте заявку</b>

<b>Имя:</b> {escape(lead_name)}
<b>Телефон:</b> {escape(phone)}
<b>Задача:</b> {escape(task)}

Всё верно?"""


def lead_created(lead: Lead) -> str:
    return f"""✅ <b>Заявка #{lead.id} принята</b>

Администратор получил её и свяжется с вами в течение рабочего дня.
Статус можно посмотреть в «Мои заявки»."""


def my_leads(leads: list[Lead]) -> str:
    if not leads:
        return NO_LEADS

    lines = ["<b>Мои заявки</b>", ""]
    for lead in leads:
        created = lead.created_at.astimezone(MSK).strftime("%d.%m.%Y %H:%M")
        lines.append(f"<b>#{lead.id}</b> · {lead.status.label} · {created}")
        task = escape(lead.task)
        if len(task) > 90:
            task = f"{task[:87]}..."
        lines.append(f"<i>{task}</i>")
        lines.append("")
    return "\n".join(lines).strip()


def admin_card(lead: Lead) -> str:
    created = lead.created_at.astimezone(MSK).strftime("%d.%m.%Y %H:%M")
    username = f"@{escape(lead.username)}" if lead.username else "не указан"
    return f"""{lead.status.label} · <b>заявка #{lead.id}</b>

<b>Имя:</b> {escape(lead.name)}
<b>Телефон:</b> {escape(lead.phone)}
<b>Telegram:</b> {username}
<b>Задача:</b> {escape(lead.task)}

<i>Создана {created}</i>"""


def lead_list(leads: list[Lead]) -> str:
    if not leads:
        return "Заявок пока нет."

    lines = ["<b>Последние заявки</b>", ""]
    for lead in leads:
        created = lead.created_at.astimezone(MSK).strftime("%d.%m %H:%M")
        task = escape(lead.task)
        if len(task) > 70:
            task = f"{task[:67]}..."
        lines.append(f"<b>#{lead.id}</b> · {lead.status.label} · {created}")
        lines.append(f"{escape(lead.name)}, {escape(lead.phone)}")
        lines.append(f"<i>{task}</i>")
        lines.append("")
    return "\n".join(lines).strip()


def stats(stats: dict[str, int]) -> str:
    done = stats["done"]
    total = stats["total"]
    conversion = round(done / total * 100) if total else 0
    return f"""<b>Статистика</b>

Всего заявок: <b>{total}</b>
🆕 Новые: {stats["new"]}
🛠 В работе: {stats["in_progress"]}
✅ Выполнено: {done}
❌ Отклонено: {stats["rejected"]}

Сегодня: {stats["today"]}
За 7 дней: {stats["week"]}
Конверсия в выполнение: {conversion}%"""


ADMIN_HELP = """<b>Админ-панель</b>

/leads: последние заявки и смена статусов
/stats: сводка за сегодня и неделю
/export: выгрузка всех заявок в CSV"""


def status_changed(lead: Lead) -> str:
    return f"{lead.status.label} · <b>заявка #{lead.id}</b>"


def notify_user_status(lead: Lead) -> str:
    if lead.status is LeadStatus.DONE:
        return f"""✅ <b>Заявка #{lead.id} выполнена</b>

Спасибо за обращение. Если нужны доработки, просто ответьте на это сообщение."""
    if lead.status is LeadStatus.REJECTED:
        return f"""Заявка #{lead.id} закрыта.

Если это ошибка или планы изменились, оставьте новую заявку: я на связи."""
    return f"🛠 <b>Заявка #{lead.id}</b> взята в работу. Напишу, как только появятся вопросы."
