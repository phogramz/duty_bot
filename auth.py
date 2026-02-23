import logging
import os
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)

# Берем код доступа из переменной окружения
ACCESS_CODE = os.getenv('ACCESS_CODE')

# Проверяем, что пароль задан
if not ACCESS_CODE:
    logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: ACCESS_CODE не задан в .env файле!")
    # Можно даже остановить бота, но мы просто залогируем
    # и установим None, чтобы проверка всегда проваливалась
    ACCESS_CODE = None

# Хранилище авторизованных пользователей (в памяти)
authorized_users = set()


class AuthStates(StatesGroup):
    """Состояния для авторизации"""
    waiting_for_code = State()


async def is_authorized(user_id: int) -> bool:
    """Проверяет, авторизован ли пользователь"""
    return user_id in authorized_users


async def request_auth(message: types.Message, state: FSMContext):
    """Запрашивает код доступа"""
    # Проверяем, что пароль вообще задан
    if ACCESS_CODE is None:
        await message.answer(
            "❌ Ошибка конфигурации: пароль доступа не задан.\n"
            "Обратитесь к администратору."
        )
        logger.error(f"Попытка доступа при отсутствующем ACCESS_CODE от user {message.from_user.id}")
        return

    await state.set_state(AuthStates.waiting_for_code)
    await message.answer(
        "🔐 Для доступа к боту введите код-пароль:"
    )


async def check_auth_code(message: types.Message, state: FSMContext):
    """Проверяет введенный код"""
    user_id = message.from_user.id
    code = message.text.strip()

    # Проверяем, что пароль задан
    if ACCESS_CODE is None:
        await message.answer("❌ Ошибка конфигурации сервера.")
        logger.error(f"Попытка ввода кода при отсутствующем ACCESS_CODE от user {user_id}")
        return False

    if code == ACCESS_CODE:
        authorized_users.add(user_id)
        await state.clear()
        await message.answer(
            "✅ Код принят! Теперь вам доступны все команды.\n"
            "Нажмите /start для начала работы."
        )
        logger.info(f"User {user_id} авторизовался")
        return True
    else:
        await message.answer("❌ Неверный код. Попробуйте еще раз:")
        return False


logger.info(f"Auth module initialized. Access code is {'set' if ACCESS_CODE else 'NOT SET - ACCESS DENIED'}")