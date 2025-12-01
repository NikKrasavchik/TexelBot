import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()

@dataclass
class BotConfig:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")

    # Texel / RapidAPI
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY_HERE")

    # БД
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "texel_bot.db")

    # Папка для временных файлов
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")

    MAX_REQUESTS_PER_DAY: int = int(os.getenv("MAX_REQUESTS_PER_DAY", "50"))

    # Ollama (локальный LLM)
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "http://localhost:11434/v1")
    AI_MODEL: str = os.getenv("AI_MODEL", "llama3")
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.8"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "800"))

config = BotConfig()
