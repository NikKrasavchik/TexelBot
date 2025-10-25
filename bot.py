"""
Основной модуль Creative Items Telegram Bot
Асинхронный бот для генерации креативных идей из предметов
"""
import asyncio
import logging
import re
from datetime import datetime
from typing import List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

from config import config
from database import DatabaseManager
from ai_engine import AIEngine

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация компонентов
db = DatabaseManager(config.DATABASE_NAME)
ai_engine = AIEngine(config.OPENAI_API_KEY)


class CreativeBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.db = db
        self.ai = ai_engine
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        self.db.add_or_update_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        welcome_text = f"""
🎨 **Привет, {user.first_name}!**

Я — *Creative Items Bot* 🤖✨

🔮 **Что я умею:**
• Принимаю список вещей
• Генерирую креативные идеи проектов
• Предлагаю DIY-решения любой сложности

📦 **Как пользоваться:**
1️⃣ Отправь мне предметы (каждый с новой строки или через запятую)
2️⃣ Нажми кнопку "🚀 Сгенерировать идеи"
3️⃣ Получи крутые варианты проектов!

💡 **Пример:**
