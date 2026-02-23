import asyncio
import logging
import aiosqlite
from datetime import datetime, date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from aiogram.enums.parse_mode import ParseMode

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация
DATABASE_PATH = 'duty_bot.db'  # путь к базе данных
TIMEZONE = timezone('Europe/Moscow')
MORNING_HOUR = 6  # 6:00 UDC, 9:00 MSK


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

    # Проверка за 3 дня - в 9:30
    scheduler.add_job(
        check_three_days_duty,
        CronTrigger(hour=MORNING_HOUR, minute=30),  # на 30 минут позже, чтобы не пересекались
        args=[bot],
        id='three_days_reminder',
        replace_existing=True
    )

    # Ежемесячное напоминание - 25 числа в 18:00
    scheduler.add_job(
        send_monthly_reminder,
        CronTrigger(day=25, hour=15, minute=0),
        args=[bot],
        id='monthly_reminder',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Планировщик уведомлений запущен")
    logger.info(f"Утренние уведомления: {MORNING_HOUR}:00")
    logger.info(f"Уведомления за 3 дня: {MORNING_HOUR}:05")
    logger.info(f"Ежемесячные напоминания: 25 число в 18:00")

    return scheduler


async def send_monthly_reminder(bot):
    """Отправляет напоминание всем пользователям 25 числа каждого месяца в 18:00"""
    logger.info("Запуск ежемесячного напоминания о бронировании")

    # Получаем всех пользователей из БД
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute('SELECT telegram_id, full_name FROM users') as cursor:
            users = await cursor.fetchall()

    if not users:
        logger.info("Нет пользователей для рассылки")
        return

    # Определяем следующий месяц
    today = date.today()
    if today.month == 12:
        next_month = 1
        next_year = today.year + 1
    else:
        next_month = today.month + 1
        next_year = today.year

    # Название следующего месяца
    month_names = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель",
        5: "май", 6: "июнь", 7: "июль", 8: "август",
        9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
    }
    next_month_name = month_names[next_month]

    # Текст сообщения
    message_text = (
        f"📅 **Напоминание о бронировании!**\n\n"
        f"Скоро наступит {next_month_name} {next_year}!\n"
        f"Не забудьте забронировать дни для дежурства по уборке.\n\n"
        f"Доступные дни: среда, суббота и воскресенье.\n"
        f"Можно записываться по 2 человека на день.\n\n"
        f"👉 Откройте бота и нажмите «Забронировать»"
    )

    # Отправляем всем пользователям
    success_count = 0
    fail_count = 0

    for user in users:
        try:
            await bot.send_message(
                chat_id=user[0],
                text=message_text,
                parse_mode=ParseMode.MARKDOWN
            )
            success_count += 1
            # Небольшая задержка, чтобы не спамить
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Не удалось отправить пользователю {user[0]}: {e}")
            fail_count += 1

    logger.info(f"Ежемесячное напоминание отправлено. Успешно: {success_count}, Ошибок: {fail_count}")

# Для тестирования - можно раскомментировать
# async def test_reminders(bot):
#     """Тестовая функция для проверки уведомлений"""
#     logger.info("Тестовый запуск уведомлений")
#     await check_today_duty(bot)
#     await check_three_days_duty(bot)