import logging
import aiosqlite
from datetime import datetime, date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация
DATABASE_PATH = 'duty_bot.db'  # путь к базе данных
TIMEZONE = timezone('Europe/Moscow')
MORNING_HOUR = 9  # 9 утра


async def send_reminder(bot, telegram_id: int, text: str):
    """Отправляет сообщение пользователю"""
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        logger.info(f"Уведомление отправлено пользователю {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю {telegram_id}: {e}")
        return False


async def check_today_duty(bot):
    """Проверяет дежурства на сегодня и отправляет уведомления"""
    today = date.today()
    logger.info(f"Проверка дежурств на сегодня: {today}")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Ищем дежурства на сегодня, у которых еще не было утреннего уведомления
        async with db.execute('''
            SELECT b.*, u.telegram_id, u.full_name 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.booking_date = ? AND b.reminder_morning_sent = 0
        ''', (today.isoformat(),)) as cursor:
            today_bookings = await cursor.fetchall()

        if not today_bookings:
            logger.info(f"На сегодня нет дежурств или все уже получили уведомления")
            return

        for booking in today_bookings:
            # Отправляем уведомление
            text = (
                f"🔔 Напоминание: сегодня ваше дежурство по уборке!\n\n"
                f"Не забудьте выполнить уборку. Спасибо за ваш вклад! 🧹"
            )

            success = await send_reminder(bot, booking['telegram_id'], text)

            if success:
                # Отмечаем, что уведомление отправлено
                await db.execute(
                    'UPDATE bookings SET reminder_morning_sent = 1 WHERE id = ?',
                    (booking['id'],)
                )
                await db.commit()
                logger.info(f"Отметили уведомление для брони {booking['id']}")


async def check_three_days_duty(bot):
    """Проверяет дежурства через 3 дня и отправляет уведомления"""
    target_date = date.today() + timedelta(days=3)
    logger.info(f"Проверка дежурств через 3 дня: {target_date}")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Ищем дежурства через 3 дня, у которых еще не было уведомления
        async with db.execute('''
            SELECT b.*, u.telegram_id, u.full_name 
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.booking_date = ? AND b.reminder_3day_sent = 0
        ''', (target_date.isoformat(),)) as cursor:
            upcoming_bookings = await cursor.fetchall()

        if not upcoming_bookings:
            logger.info(f"На дату {target_date} нет дежурств или все уже получили уведомления")
            return

        for booking in upcoming_bookings:
            # Форматируем дату для сообщения
            date_obj = datetime.strptime(booking['booking_date'], '%Y-%m-%d').date()
            date_str = date_obj.strftime('%d.%m.%Y')

            # Отправляем уведомление
            text = (
                f"📅 Напоминание: через 3 дня, {date_str}, ваше дежурство по уборке.\n\n"
                f"При необходимости, пожалуйста, запланируйте замену заранее."
            )

            success = await send_reminder(bot, booking['telegram_id'], text)

            if success:
                # Отмечаем, что уведомление отправлено
                await db.execute(
                    'UPDATE bookings SET reminder_3day_sent = 1 WHERE id = ?',
                    (booking['id'],)
                )
                await db.commit()
                logger.info(f"Отметили уведомление за 3 дня для брони {booking['id']}")


def setup_reminders(bot):
    """Настраивает и запускает планировщик уведомлений"""
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # Утренняя проверка (в день дежурства) - каждый день в 9:00
    scheduler.add_job(
        check_today_duty,
        CronTrigger(hour=MORNING_HOUR, minute=0),
        args=[bot],
        id='morning_reminder',
        replace_existing=True
    )

    # Проверка за 3 дня - тоже в 9:00
    scheduler.add_job(
        check_three_days_duty,
        CronTrigger(hour=MORNING_HOUR, minute=5),  # на 5 минут позже, чтобы не пересекались
        args=[bot],
        id='three_days_reminder',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Планировщик уведомлений запущен")
    logger.info(f"Утренние уведомления: {MORNING_HOUR}:00")
    logger.info(f"Уведомления за 3 дня: {MORNING_HOUR}:05")

    return scheduler

# Для тестирования - можно раскомментировать
# async def test_reminders(bot):
#     """Тестовая функция для проверки уведомлений"""
#     logger.info("Тестовый запуск уведомлений")
#     await check_today_duty(bot)
#     await check_three_days_duty(bot)