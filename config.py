"""
Конфигурация для Creative Items Bot
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
    
    # Ollama настройки
    AI_MODEL: str = os.getenv("AI_MODEL", "llama3.2")
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "http://localhost:11434/v1")
    
    # Настройки базы данных
    DATABASE_NAME: str = "creative_bot.db"
    
    # Настройки AI
    AI_TEMPERATURE: float = 0.85
    MAX_TOKENS: int = 800
    
    # Лимиты
    MAX_ITEMS_PER_USER: int = 20
    MAX_IDEAS_PER_REQUEST: int = 7
    MIN_ITEMS_FOR_IDEAS: int = 2
    
    # Антиспам
    COOLDOWN_SECONDS: int = 3
    MAX_REQUESTS_PER_MINUTE: int = 10

config = BotConfig()
