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
    """Календарь - показываем ТОЛЬКО доступные дни (ср, сб, вс)"""
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

    # Получаем все доступные дни месяца
    available_days = []
    if month == 12:
        last_day = 31
    else:
        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day

    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        if current_date.weekday() in allowed_weekdays:
            available_days.append(day)

    # Группируем доступные дни по 3 в ряд
    for i in range(0, len(available_days), 3):
        row_days = available_days[i:i + 3]
        row_buttons = []

        for day in row_days:
            current_date = date(year, month, day)
            date_str = current_date.isoformat()
            count = bookings_data.get(date_str, 0)

            # Формируем текст: число и количество
            if count == 0:
                btn_text = f"{day:02d} (0/2)"
            elif count == 1:
                btn_text = f"{day:02d} (1/2)"
            else:
                btn_text = f"{day:02d} (2/2)"

            callback = f"select_{year}_{month}_{day}" if count < 2 else "ignore"
            row_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=callback))

        builder.row(*row_buttons, width=len(row_days))

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