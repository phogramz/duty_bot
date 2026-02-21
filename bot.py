import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums.parse_mode import ParseMode

import config
import database

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем бота и диспетчер
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()


# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Приветственное сообщение и регистрация пользователя"""

    # Регистрируем пользователя в БД
    await database.add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    # Получаем информацию о пользователе (для примера)
    user = await database.get_user(message.from_user.id)

    # Создаем клавиатуру с основными кнопками
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📅 Забронировать", callback_data="book"),
                types.InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings")
            ],
            [
                types.InlineKeyboardButton(text="👥 Все дежурства", callback_data="all_bookings"),
                types.InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_menu")
            ]
        ]
    )

    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        f"Это бот для бронирования дежурств по уборке.\n"
        f"Доступные дни: среда, суббота, воскресенье.\n\n"
        f"Выбери действие:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


# Заглушки для будущих обработчиков
@dp.callback_query(lambda c: c.data == 'book')
async def process_book(callback: types.CallbackQuery):
    await callback.message.edit_text("🚧 Скоро здесь будет календарь для бронирования")
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'my_bookings')
async def process_my_bookings(callback: types.CallbackQuery):
    await callback.message.edit_text("🚧 Здесь будут ваши брони")
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'all_bookings')
async def process_all_bookings(callback: types.CallbackQuery):
    await callback.message.edit_text("🚧 Здесь будут все дежурства")
    await callback.answer()


@dp.callback_query(lambda c: c.data == 'cancel_menu')
async def process_cancel_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🚧 Здесь можно будет отменить бронь")
    await callback.answer()


# Запуск бота
async def main():
    # Инициализируем базу данных
    await database.init_db()

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())