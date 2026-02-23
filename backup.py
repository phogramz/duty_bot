#!/usr/bin/env python3
import os
import sqlite3
import datetime
import asyncio
import logging
from pathlib import Path
from aiogram import Bot
import config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ID администратора (ваш Telegram ID)
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))


async def create_backup():
    """Создает бэкап базы данных и отправляет админу"""

    # Создаем папку для бэкапов, если её нет
    backup_dir = Path("/root/duty_bot/backups")
    backup_dir.mkdir(exist_ok=True)

    # Имя файла с датой
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"duty_bot_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    try:
        # Создаем бэкап SQLite
        source = sqlite3.connect(config.DATABASE_PATH)
        dest = sqlite3.connect(str(backup_path))

        source.backup(dest)

        dest.close()
        source.close()

        logger.info(f"✅ Бэкап создан: {backup_filename}")

        # Отправляем бэкап админу
        await send_backup_to_admin(backup_path, backup_filename)

        # Удаляем старые бэкапы (оставляем последние 5)
        clean_old_backups(backup_dir, keep_last=5)

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка создания бэкапа: {e}")
        return False


async def send_backup_to_admin(file_path: Path, filename: str):
    """Отправляет файл бэкапа администратору"""
    from aiogram import Bot
    bot = Bot(token=config.BOT_TOKEN)

    try:
        # Проверим, что файл существует
        if not file_path.exists():
            logger.error(f"Файл {file_path} не найден")
            return False

        # Отправляем файл
        with open(file_path, 'rb') as f:
            await bot.send_document(
                chat_id=ADMIN_ID,
                document=f,
                caption=f"📦 **Автоматический бэкап**\n"
                        f"📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                        f"📁 Размер: {file_path.stat().st_size / 1024:.1f} KB"
            )

        logger.info(f"✅ Бэкап отправлен админу {ADMIN_ID}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка отправки бэкапа: {e}")
        return False

    finally:
        await bot.session.close()


def clean_old_backups(backup_dir: Path, keep_last: int = 5):
    """Удаляет старые бэкапы, оставляя только последние keep_last штук"""
    backups = sorted(backup_dir.glob("duty_bot_backup_*.db"), key=os.path.getmtime)

    # Удаляем старые бэкапы (кроме последних keep_last)
    for old_backup in backups[:-keep_last]:
        old_backup.unlink()
        logger.info(f"Удален старый бэкап: {old_backup.name}")


async def main():
    """Запуск бэкапа"""
    success = await create_backup()
    if success:
        logger.info("✅ Бэкап завершен успешно")
    else:
        logger.error("❌ Бэкап не удался")


if __name__ == "__main__":
    asyncio.run(main())