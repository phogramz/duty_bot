import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_PATH = 'duty_bot.db'

if not BOT_TOKEN:
    raise ValueError("Нет BOT_TOKEN в .env файле!")