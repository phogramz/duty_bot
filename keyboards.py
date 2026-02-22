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
    return builder.as_markup() # 👤 👥 🟩 🟨 🟥


def get_calendar_keyboard(year: int, month: int, bookings_data: dict = None) -> InlineKeyboardMarkup:
    """Календарь с пустыми ячейками для других дней, но заголовки только для ср,сб,вс"""
    builder = InlineKeyboardBuilder()
    allowed_weekdays = [2, 5, 6]  # ср, сб, вс
    weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

    # Эмодзи для количества человек
    people_emoji = {
        0: "🟩",
        1: "🟨",
        2: "🟥"
    }

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

    # Заголовки дней недели - ТОЛЬКО для ср, сб, вс
    builder.row(
        InlineKeyboardButton(text="Ср", callback_data="ignore"),
        InlineKeyboardButton(text="Сб", callback_data="ignore"),
        InlineKeyboardButton(text="Вс", callback_data="ignore"),
        width=3
    )

    # Определяем первый день месяца
    first_day = date(year, month, 1)
    start_weekday = first_day.weekday()  # 0=пн, 1=вт, 2=ср, 3=чт, 4=пт, 5=сб, 6=вс

    # Определяем последний день месяца
    if month == 12:
        last_day = 31
    else:
        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day

    # Создаем сетку 7x(кол-во недель) для всех дней
    all_days = []
    current_date = first_day
    while current_date.month == month:
        all_days.append({
            'day': current_date.day,
            'weekday': current_date.weekday(),
            'date': current_date,
            'date_str': current_date.isoformat()
        })
        current_date += timedelta(days=1)

    # Добавляем пустые дни в начало, если месяц начинается не с понедельника
    days_grid = []
    # Добавляем пустые дни до первого дня месяца
    for _ in range(start_weekday):
        days_grid.append(None)  # None означает пустую ячейку

    # Добавляем все дни месяца
    days_grid.extend(all_days)

    # Добавляем пустые дни в конец, чтобы получить полные недели
    while len(days_grid) % 7 != 0:
        days_grid.append(None)

    # Разбиваем на недели по 7 дней
    weeks = [days_grid[i:i + 7] for i in range(0, len(days_grid), 7)]

    # Для каждой недели создаем ряд с ТОЛЬКО доступными днями (ср, сб, вс)
    for week in weeks:
        row_buttons = []

        # Проходим по каждому дню недели (пн-вс)
        for day_idx, day_info in enumerate(week):
            # Проверяем, является ли этот день доступным (ср, сб, вс)
            if day_info and day_info['weekday'] in allowed_weekdays:
                count = bookings_data.get(day_info['date_str'], 0)

                # Формат: число | количество/2 + эмодзи
                btn_text = f"{day_info['day']:02d} | {count}/2 {people_emoji[count]}"
                callback = f"select_{year}_{month}_{day_info['day']}" if count < 2 else "ignore"
                row_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=callback))
            else:
                # Для всех остальных дней (включая пустые) - пустая кнопка
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        # Добавляем ряд с 7 кнопками (но визуально видны только ср,сб,вс)
        builder.row(*row_buttons, width=7)

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