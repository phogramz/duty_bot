from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date, timedelta
import calendar
from utils import get_available_days, format_date_short, get_month_name


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Забронировать", callback_data="book"),
        InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="👥 Все дежурства", callback_data="all_bookings"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_menu"),
        width=2
    )
    return builder.as_markup()


def get_calendar_keyboard(year: int, month: int, bookings_data: dict = None) -> InlineKeyboardMarkup:
    """Календарь на указанный месяц (СИНХРОННЫЙ)

    Args:
        year: год
        month: месяц
        bookings_data: словарь {дата: количество_броней}
                      например {'2024-03-04': 1, '2024-03-08': 2}
    """
    builder = InlineKeyboardBuilder()
    allowed_weekdays = [2, 5, 6]  # ср, сб, вс

    if bookings_data is None:
        bookings_data = {}

    # Заголовок с навигацией
    month_name = get_month_name(month)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text=f"{month_name} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_{next_year}_{next_month}"),
        width=3
    )

    # Заголовки дней недели (короткие)
    builder.row(
        *[InlineKeyboardButton(text=d, callback_data="ignore") for d in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']],
        width=7
    )

    # Определяем первый день месяца
    first_day = date(year, month, 1)
    start_weekday = first_day.weekday()

    # Пустые ячейки перед первым днем
    week = []
    for _ in range(start_weekday):
        week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

    # Заполняем дни месяца
    if month == 12:
        last_day = 31
    else:
        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day

    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        date_str = current_date.isoformat()

        if current_date.weekday() in allowed_weekdays:
            count = bookings_data.get(date_str, 0)

            # ОЧЕНЬ КОРОТКИЙ формат: просто число и эмодзи
            if count == 0:
                btn_text = f"{day}\n⬜"  # белый квадрат
            elif count == 1:
                btn_text = f"{day}\n🟨"  # желтый (1 человек)
            else:
                btn_text = f"{day}\n🟥"  # красный (занято)

            callback = f"select_{year}_{month}_{day}" if count < 2 else "ignore"
        else:
            # Для недоступных дней - просто точка или пробел
            btn_text = "❌"
            callback = "ignore"

        week.append(InlineKeyboardButton(text=btn_text, callback_data=callback))

        if len(week) == 7:
            builder.row(*week, width=7)
            week = []

    if week:
        while len(week) < 7:
            week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
        builder.row(*week, width=7)

    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_menu"), width=1)

    return builder.as_markup()


def get_booking_confirmation_keyboard(date_str: str) -> InlineKeyboardMarkup:
    """Подтверждение бронирования"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{date_str}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_calendar"),
        width=2
    )
    return builder.as_markup()


def get_cancel_selection_keyboard(bookings: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора брони для отмены"""
    builder = InlineKeyboardBuilder()

    for booking in bookings:
        date_obj = datetime.strptime(booking['booking_date'], '%Y-%m-%d').date()
        btn_text = format_date_short(date_obj)
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {btn_text}",
                callback_data=f"cancel_{booking['id']}"
            ),
            width=1
        )

    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_menu"), width=1)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура с кнопкой назад"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_menu"), width=1)
    return builder.as_markup()