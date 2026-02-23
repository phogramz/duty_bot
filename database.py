import aiosqlite
import config
from datetime import date


async def init_db():
    """Создает таблицы, если их нет"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Таблица пользователей (без изменений)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица броней - УБИРАЕМ UNIQUE(booking_date)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                booking_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reminder_3day_sent BOOLEAN DEFAULT 0,
                reminder_morning_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
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


async def get_bookings_by_date(date: date):
    """Получает ВСЕХ дежурных на конкретную дату"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT b.*, u.full_name, u.telegram_id 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.booking_date = ?
        ''', (date.isoformat(),)) as cursor:
            return await cursor.fetchall()  # теперь возвращает список, а не одного


async def create_booking(user_id: int, booking_date: date) -> tuple[bool, str]:
    """Создает новую бронь с проверкой лимита"""
    current_count = await get_bookings_count_for_date(booking_date)

    if current_count >= 2:
        return False, "Достигнут лимит (2 человека)"

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        try:
            # Явно указываем, что уведомления еще не отправлены
            await db.execute('''
                INSERT INTO bookings (
                    user_id, booking_date, 
                    reminder_3day_sent, reminder_morning_sent
                ) VALUES (?, ?, 0, 0)
            ''', (user_id, booking_date.isoformat()))
            await db.commit()
            return True, f"Вы {current_count + 1}-й дежурный"
        except Exception as e:
            return False, f"Ошибка: {e}"


async def get_user_bookings(telegram_id: int):
    """Получает все брони пользователя"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT b.*, u.full_name 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY b.booking_date
        ''', (telegram_id,)) as cursor:
            return await cursor.fetchall()


async def cancel_booking(booking_id: int, telegram_id: int):
    """Отменяет бронь (только если это бронь пользователя)"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Проверяем, что бронь принадлежит пользователю
        async with db.execute('''
            SELECT b.id FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ? AND u.telegram_id = ?
        ''', (booking_id, telegram_id)) as cursor:
            if not await cursor.fetchone():
                return False

        await db.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
        await db.commit()
        return True


async def get_all_bookings():
    """Получает все брони для общего календаря"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT b.booking_date, u.full_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            ORDER BY b.booking_date
        ''') as cursor:
            return await cursor.fetchall()


async def get_bookings_count_for_date(date: date) -> int:
    """Сколько человек уже записалось на конкретную дату"""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute('''
            SELECT COUNT(*) as count 
            FROM bookings 
            WHERE booking_date = ?
        ''', (date.isoformat(),)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0


async def get_month_bookings(year: int, month: int):
    """Получает все брони за указанный месяц"""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute('''
            SELECT booking_date FROM bookings 
            WHERE booking_date >= ? AND booking_date < ?
        ''', (start_date.isoformat(), end_date.isoformat())) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]  # возвращаем список дат


async def get_user_bookings_filtered(telegram_id: int):
    """Получает все будущие брони пользователя"""
    today = date.today().isoformat()

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT b.*, u.full_name 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE u.telegram_id = ? AND b.booking_date >= ?
            ORDER BY b.booking_date
        ''', (telegram_id, today)) as cursor:
            return await cursor.fetchall()


async def get_all_future_bookings():
    """Получает все будущие брони для общего календаря"""
    today = date.today().isoformat()

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT b.booking_date, u.full_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.booking_date >= ?
            ORDER BY b.booking_date
        ''', (today,)) as cursor:
            return await cursor.fetchall()