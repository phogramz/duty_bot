import asyncio
import logging
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import config
import database
import keyboards as kb
from utils import format_date_long, format_date_short, get_month_name

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# Состояния для FSM (Finite State Machine)
class BookingStates(StatesGroup):
    selecting_date = State()
    confirming = State()


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение и регистрация пользователя"""
    await database.add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        f"Это бот для бронирования дежурств по уборке.\n"
        f"Доступные дни: среда, суббота, воскресенье.\n\n"
        f"Выбери действие:",
        reply_markup=kb.get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )


# Обработка кнопки "Забронировать"
@dp.callback_query(F.data == "book")
async def process_book(callback: CallbackQuery):
    """Показывает календарь на текущий месяц"""
    today = date.today()
    await callback.message.edit_text(
        f"📅 Выберите день для дежурства:\n"
        f"Доступны только среда, суббота и воскресенье.",
        reply_markup=kb.get_calendar_keyboard(today.year, today.month)
    )
    await callback.answer()


# Обработка навигации по календарю
@dp.callback_query(F.data.startswith("cal_"))
async def process_calendar_nav(callback: CallbackQuery):
    """Переключение между месяцами"""
    _, year, month = callback.data.split('_')
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_calendar_keyboard(int(year), int(month))
    )
    await callback.answer()


# Обработка выбора даты
@dp.callback_query(F.data.startswith("select_"))
async def process_date_select(callback: CallbackQuery):
    """Пользователь выбрал дату в календаре"""
    _, year, month, day = callback.data.split('_')
    selected_date = date(int(year), int(month), int(day))

    # Проверяем, свободен ли день
    existing = await database.get_bookings_by_date(selected_date)

    if existing:
        await callback.message.edit_text(
            f"❌ Этот день ({format_date_long(selected_date)}) уже занят пользователем {existing['full_name']}.\n"
            f"Выберите другой день.",
            reply_markup=kb.get_back_keyboard()
        )
    else:
        # Спрашиваем подтверждение
        await callback.message.edit_text(
            f"✅ Вы выбрали {format_date_long(selected_date)}.\n"
            f"Подтверждаете бронирование?",
            reply_markup=kb.get_booking_confirmation_keyboard(f"{year}-{month:02d}-{day:02d}")
        )

    await callback.answer()


# Обработка подтверждения брони
@dp.callback_query(F.data.startswith("confirm_"))
async def process_confirm(callback: CallbackQuery):
    """Подтверждение бронирования"""
    date_str = callback.data.replace("confirm_", "")
    booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # Создаем бронь
    user = await database.get_user(callback.from_user.id)
    success = await database.create_booking(user['id'], booking_date)

    if success:
        await callback.message.edit_text(
            f"✅ Дежурство на {format_date_long(booking_date)} успешно забронировано!\n"
            f"Я напомню вам за 3 дня и утром в день дежурства.",
            reply_markup=kb.get_back_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"❌ К сожалению, этот день уже кто-то забронировал.\n"
            f"Попробуйте выбрать другой день.",
            reply_markup=kb.get_back_keyboard()
        )

    await callback.answer()


# Обработка кнопки "Мои брони"
@dp.callback_query(F.data == "my_bookings")
async def process_my_bookings(callback: CallbackQuery):
    """Показывает список броней пользователя"""
    bookings = await database.get_user_bookings(callback.from_user.id)

    if not bookings:
        await callback.message.edit_text(
            "📭 У вас пока нет забронированных дежурств.\n"
            "Нажмите «Забронировать», чтобы выбрать день.",
            reply_markup=kb.get_back_keyboard()
        )
        await callback.answer()
        return

    # Группируем брони по месяцам
    bookings_by_month = {}
    for booking in bookings:
        date_obj = datetime.strptime(booking['booking_date'], '%Y-%m-%d').date()
        month_key = f"{get_month_name(date_obj.month)} {date_obj.year}"
        if month_key not in bookings_by_month:
            bookings_by_month[month_key] = []
        bookings_by_month[month_key].append(format_date_short(date_obj))

    # Формируем сообщение
    text = "📋 **Ваши дежурства:**\n\n"
    for month, dates in bookings_by_month.items():
        text += f"**{month}:**\n"
        text += ", ".join(dates) + "\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.get_back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


# Обработка кнопки "Отменить"
@dp.callback_query(F.data == "cancel_menu")
async def process_cancel_menu(callback: CallbackQuery):
    """Показывает список броней для отмены"""
    bookings = await database.get_user_bookings(callback.from_user.id)

    if not bookings:
        await callback.message.edit_text(
            "📭 У вас нет броней для отмены.",
            reply_markup=kb.get_back_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "❌ Выберите дежурство для отмены:",
        reply_markup=kb.get_cancel_selection_keyboard(bookings)
    )
    await callback.answer()


# Обработка отмены конкретной брони
@dp.callback_query(F.data.startswith("cancel_"))
async def process_cancel_booking(callback: CallbackQuery):
    """Отменяет выбранную бронь"""
    booking_id = int(callback.data.replace("cancel_", ""))
    success = await database.cancel_booking(booking_id, callback.from_user.id)

    if success:
        await callback.message.edit_text(
            "✅ Бронь успешно отменена!",
            reply_markup=kb.get_back_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось отменить бронь. Возможно, она уже была отменена.",
            reply_markup=kb.get_back_keyboard()
        )

    await callback.answer()


# Обработка кнопки "Все дежурства"
@dp.callback_query(F.data == "all_bookings")
async def process_all_bookings(callback: CallbackQuery):
    """Показывает календарь со всеми дежурствами"""
    all_bookings = await database.get_all_bookings()

    if not all_bookings:
        await callback.message.edit_text(
            "📭 Пока нет ни одного дежурства.\n"
            "Будьте первым! Нажмите «Забронировать».",
            reply_markup=kb.get_back_keyboard()
        )
        await callback.answer()
        return

    # Группируем по месяцам
    bookings_by_month = {}
    for booking in all_bookings:
        date_obj = datetime.strptime(booking['booking_date'], '%Y-%m-%d').date()
        month_key = f"{get_month_name(date_obj.month)} {date_obj.year}"
        if month_key not in bookings_by_month:
            bookings_by_month[month_key] = []
        bookings_by_month[month_key].append(
            f"{format_date_short(date_obj)} — {booking['full_name']}"
        )

    # Формируем сообщение
    text = "👥 **Все дежурства:**\n\n"
    for month, entries in bookings_by_month.items():
        text += f"**{month}:**\n"
        text += "\n".join(entries) + "\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=kb.get_back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


# Обработка кнопки "Назад"
@dp.callback_query(F.data == "back_to_menu")
async def process_back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=kb.get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_calendar")
async def process_back_to_calendar(callback: CallbackQuery):
    """Возврат к календарю"""
    today = date.today()
    await callback.message.edit_text(
        "📅 Выберите день для дежурства:",
        reply_markup=kb.get_calendar_keyboard(today.year, today.month)
    )
    await callback.answer()


# Игнорирование пустых кнопок
@dp.callback_query(F.data == "ignore")
async def process_ignore(callback: CallbackQuery):
    """Игнорирует нажатия на неактивные кнопки"""
    await callback.answer()


# Запуск бота
async def main():
    await database.init_db()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())