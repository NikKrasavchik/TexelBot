"""
Конфигурация для Texel Try-On Bot
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class BotConfig:
    """Основная конфигурация бота"""
    # Telegram
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    # RapidAPI (Texel)
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY_HERE")
    
    # Настройки базы данных
    DATABASE_NAME: str = "texel_bot.db"
    
    # Лимиты
    MAX_REQUESTS_PER_DAY: int = 50
    
    # Путь для временных файлов
    TEMP_DIR: str = "temp_images"

config = BotConfig()
