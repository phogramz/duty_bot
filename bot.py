import asyncio
import logging
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from reminder import setup_reminders
from functools import wraps

import config
import database
import keyboards as kb
from utils import format_date_long, format_date_short, get_month_name
from auth import is_authorized, request_auth, check_auth_code, AuthStates

import gc
gc.set_threshold(100, 5, 5)
gc.enable()

import logging
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('aiogram').setLevel(logging.INFO)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

from functools import wraps


def auth_required(handler):
    """Декоратор для проверки авторизации в callback-обработчиках"""

    @wraps(handler)
    async def wrapper(callback: types.CallbackQuery, *args, **kwargs):
        # Проверка авторизации
        if not await is_authorized(callback.from_user.id):
            await callback.answer("🔐 Требуется авторизация", show_alert=True)
            # Получаем state из kwargs (aiogram передает его в обработчики)
            state = kwargs.get('state')
            if state:
                await request_auth(callback.message, state)
            return

        # Если авторизован, вызываем исходный обработчик
        return await handler(callback, *args, **kwargs)

    return wrapper


@dp.message(AuthStates.waiting_for_code)
async def handle_auth_code(message: types.Message, state: FSMContext):
    """Обрабатывает ввод кода доступа"""
    await check_auth_code(message, state)


# Состояния для FSM (Finite State Machine)
class BookingStates(StatesGroup):
    selecting_date = State()
    confirming = State()


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Стартовая команда"""
    user_id = message.from_user.id

    if await is_authorized(user_id):
        # Уже авторизован - показываем меню
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
            reply_markup=kb.get_main_keyboard()
        )
    else:
        # Не авторизован - запрашиваем код
        await request_auth(message, state)


# Обработка кнопки "Забронировать"
@dp.callback_query(F.data == "book")
@auth_required
async def process_book(callback: CallbackQuery):
    """Показывает календарь на текущий месяц"""
    today = date.today()

    # Загружаем СВЕЖИЕ данные о бронях
    month_bookings = await database.get_month_bookings(today.year, today.month)

    # Преобразуем в словарь {дата: количество}
    bookings_count = {}
    for booking in month_bookings:
        # booking может быть строкой или кортежем
        if isinstance(booking, (tuple, list)):
            date_str = booking[0]
        elif isinstance(booking, str):
            date_str = booking
        else:
            date_str = booking['booking_date']  # если Row объект
        bookings_count[date_str] = bookings_count.get(date_str, 0) + 1

    # Логируем для отладки
    print(f"Загружено броней: {bookings_count}")

    await callback.message.edit_text(
        "📅 Выберите день для дежурства:",
        reply_markup=kb.get_calendar_keyboard(
            today.year,
            today.month,
            bookings_count
        )
    )
    await callback.answer()


# Обработка навигации по календарю
@dp.callback_query(F.data.startswith("cal_"))
async def process_calendar_nav(callback: CallbackQuery):
    """Переключение между месяцами"""
    _, year, month = callback.data.split('_')
    year, month = int(year), int(month)

    # Загружаем СВЕЖИЕ данные для нового месяца
    month_bookings = await database.get_month_bookings(year, month)
    bookings_count = {}
    for booking in month_bookings:
        if isinstance(booking, (tuple, list)):
            date_str = booking[0]
        elif isinstance(booking, str):
            date_str = booking
        else:
            date_str = booking['booking_date']
        bookings_count[date_str] = bookings_count.get(date_str, 0) + 1

    await callback.message.edit_reply_markup(
        reply_markup=kb.get_calendar_keyboard(year, month, bookings_count)
    )
    await callback.answer()


# Обработка выбора даты
@dp.callback_query(F.data.startswith("select_"))
async def process_date_select(callback: CallbackQuery):
    """Пользователь выбрал дату в календаре"""
    _, year, month, day = callback.data.split('_')
    year, month, day = int(year), int(month), int(day)
    selected_date = date(year, month, day)

    # Получаем ВСЕХ дежурных на эту дату
    existing_bookings = await database.get_bookings_by_date(selected_date)
    current_count = len(existing_bookings)

    if current_count >= 2:
        await callback.message.edit_text(
            f"❌ На {format_date_long(selected_date)} уже записалось 2 человека.\n"
            f"Выберите другой день.",
            reply_markup=kb.get_back_keyboard()
        )
    elif current_count == 1:
        # Есть один дежурный, можно вторым
        await callback.message.edit_text(
            f"✅ На {format_date_long(selected_date)} уже записался {existing_bookings[0]['full_name']}.\n"
            f"Вы можете быть вторым дежурным. Подтверждаете?",
            reply_markup=kb.get_booking_confirmation_keyboard(f"{year}-{month:02d}-{day:02d}")
        )
    else:
        # Свободно
        await callback.message.edit_text(
            f"✅ Вы выбрали {format_date_long(selected_date)}.\n"
            f"Подтверждаете бронирование?",
            reply_markup=kb.get_booking_confirmation_keyboard(f"{year}-{month:02d}-{day:02d}")
        )

    await callback.answer()


# Обработка подтверждения брони
@dp.callback_query(F.data.startswith("confirm_"))
@auth_required
async def process_confirm(callback: CallbackQuery):
    """Подтверждение бронирования с автоматическим обновлением календаря"""
    date_str = callback.data.replace("confirm_", "")
    booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # Получаем пользователя
    user = await database.get_user(callback.from_user.id)
    if not user:
        await database.add_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name
        )
        user = await database.get_user(callback.from_user.id)

    # Проверяем лимит
    current_count = await database.get_bookings_count_for_date(booking_date)

    if current_count >= 2:
        # Если уже занято - показываем обновленный календарь
        today = date.today()
        month_bookings = await database.get_month_bookings(today.year, today.month)
        bookings_count = {}
        for booking in month_bookings:
            # Обрабатываем разные форматы данных
            if isinstance(booking, (tuple, list)):
                date_str = booking[0]
            elif isinstance(booking, str):
                date_str = booking
            else:
                date_str = booking['booking_date']
            bookings_count[date_str] = bookings_count.get(date_str, 0) + 1

        await callback.message.edit_text(
            f"❌ На {format_date_long(booking_date)} уже записалось 2 человека.\n\n"
            f"📅 Актуальный календарь:",
            reply_markup=kb.get_calendar_keyboard(
                today.year,
                today.month,
                bookings_count
            )
        )
        await callback.answer()
        return

    # Создаем бронь
    success, message = await database.create_booking(user['id'], booking_date)

    if success:
        # Загружаем обновленные данные для календаря
        today = date.today()
        month_bookings = await database.get_month_bookings(today.year, today.month)
        bookings_count = {}
        for booking in month_bookings:
            if isinstance(booking, (tuple, list)):
                date_str = booking[0]
            elif isinstance(booking, str):
                date_str = booking
            else:
                date_str = booking['booking_date']
            bookings_count[date_str] = bookings_count.get(date_str, 0) + 1

        # Показываем сообщение об успехе и сразу обновленный календарь
        await callback.message.edit_text(
            f"✅ Вы записаны на {format_date_long(booking_date)}!\n"
            f"Вы {current_count + 1}-й дежурный на этот день.\n\n"
            f"📅 Обновленный календарь:",
            reply_markup=kb.get_calendar_keyboard(
                today.year,
                today.month,
                bookings_count
            )
        )
    else:
        # Если ошибка - тоже показываем календарь
        today = date.today()
        month_bookings = await database.get_month_bookings(today.year, today.month)
        bookings_count = {}
        for booking in month_bookings:
            if isinstance(booking, (tuple, list)):
                date_str = booking[0]
            elif isinstance(booking, str):
                date_str = booking
            else:
                date_str = booking['booking_date']
            bookings_count[date_str] = bookings_count.get(date_str, 0) + 1

        await callback.message.edit_text(
            f"❌ Не удалось записаться: {message}\n\n"
            f"📅 Актуальный календарь:",
            reply_markup=kb.get_calendar_keyboard(
                today.year,
                today.month,
                bookings_count
            )
        )

    await callback.answer()


# Обработка кнопки "Мои брони"
@dp.callback_query(F.data == "my_bookings")
@auth_required
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
        reply_markup=kb.get_cancel_selection_keyboard(bookings)  # ДОБАВЬ AWAIT
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
@auth_required
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

    # Группируем по датам и собираем имена
    bookings_by_date = {}
    for booking in all_bookings:
        date_obj = datetime.strptime(booking['booking_date'], '%Y-%m-%d').date()
        date_key = date_obj.isoformat()
        if date_key not in bookings_by_date:
            bookings_by_date[date_key] = {
                'date': date_obj,
                'names': []
            }
        bookings_by_date[date_key]['names'].append(booking['full_name'])

    # Группируем по месяцам для вывода
    bookings_by_month = {}
    for date_key, data in bookings_by_date.items():
        month_key = f"{get_month_name(data['date'].month)} {data['date'].year}"
        if month_key not in bookings_by_month:
            bookings_by_month[month_key] = []

        # Формируем строку: "04ср — Имя1 и Имя2"
        date_str = format_date_short(data['date'])
        names_str = " и ".join(data['names'])
        bookings_by_month[month_key].append(f"{date_str} — {names_str}")

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
    """Возврат в главное меню."""
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
    # Настраиваем и запускаем планировщик уведомлений (1)
    scheduler = setup_reminders(bot)
    # Запускаем бота
    await dp.start_polling(bot)
    # При остановке бота останавливаем и планировщик
    scheduler.shutdown()


if __name__ == '__main__':
    asyncio.run(main())