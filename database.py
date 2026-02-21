import aiosqlite
import config
from datetime import date


async def init_db():
    """Создает таблицы, если их нет"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица броней
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booking_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reminder_3day_sent BOOLEAN DEFAULT 0,
                reminder_morning_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(booking_date)  -- один день - одно дежурство
            )
        ''')

        await db.commit()


async def add_user(telegram_id: int, username: str, full_name: str):
    """Добавляет нового пользователя или игнорирует, если уже есть"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
        ''', (telegram_id, username, full_name))
        await db.commit()


async def get_user(telegram_id: int):
    """Получает пользователя по telegram_id"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row  # чтобы получать записи как словари
        async with db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            return await cursor.fetchone()