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
    """Календарь - только ср, сб, вс, 3 колонки, с правильной разбивкой по неделям"""
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

    # Заголовки дней недели - только ср, сб, вс
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

    # Собираем все доступные дни с их позициями в неделе
    available_days = []
    for day in range(1, last_day + 1):
        current_date = date(year, month, day)
        weekday = current_date.weekday()
        if weekday in allowed_weekdays:
            # Определяем номер недели в месяце (1-5)
            week_num = (day + start_weekday - 1) // 7
            # Определяем позицию в ряду (0-2 для ср,сб,вс)
            pos_in_week = [2, 5, 6].index(weekday)  # 0=ср, 1=сб, 2=вс

            available_days.append({
                'day': day,
                'week_num': week_num,
                'pos': pos_in_week,
                'date': current_date,
                'date_str': current_date.isoformat()
            })

    # Группируем по неделям
    weeks = {}
    for day_info in available_days:
        week_num = day_info['week_num']
        if week_num not in weeks:
            weeks[week_num] = [None, None, None]  # [ср, сб, вс]
        weeks[week_num][day_info['pos']] = day_info

    # Сортируем недели и создаем ряды
    for week_num in sorted(weeks.keys()):
        week = weeks[week_num]
        row_buttons = []

        for pos, day_info in enumerate(week):
            if day_info:
                count = bookings_data.get(day_info['date_str'], 0)

                # Формат: число | количество/2 + эмодзи
                btn_text = f"{day_info['day']:02d} | {count}/2 {people_emoji[count]}"
                callback = f"select_{year}_{month}_{day_info['day']}" if count < 2 else "ignore"
                row_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=callback))
            else:
                # Пустая кнопка-заполнитель для сохранения структуры
                row_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))

        builder.row(*row_buttons, width=3)

    builder.row(InlineKeyboardButton(text="« Назад", callback_data="back_to_menu"), width=1)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура с кнопкой назад"""
    builder = InlineKeyboardBuilder()
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