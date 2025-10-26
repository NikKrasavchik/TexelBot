"""
Основной модуль Creative Items Telegram Bot
"""
import logging
import re
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
ai_engine = AIEngine()


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
        
        welcome_text = (
            f"🎨 Привет, {user.first_name}!\n\n"
            "Я — Creative Items Bot 🤖✨\n\n"
            "🔮 Что я умею:\n"
            "• Принимаю список вещей\n"
            "• Генерирую креативные идеи проектов\n"
            "• Предлагаю DIY-решения любой сложности\n\n"
            "📦 Как пользоваться:\n"
            "1️⃣ Отправь мне предметы (каждый с новой строки или через запятую)\n"
            "2️⃣ Нажми кнопку 'Сгенерировать идеи'\n"
            "3️⃣ Получи крутые варианты проектов!\n\n"
            "💡 Пример:\n"
            "молоток\n"
            "гвозди\n"
            "доски\n"
            "краска\n\n"
            "Попробуй прямо сейчас! 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("📚 Инструкция", callback_data="help")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "📚 Инструкция\n\n"
            "Команды:\n"
            "/start - Начать работу\n"
            "/help - Эта инструкция\n"
            "/myitems - Показать мои предметы\n"
            "/clear - Очистить список предметов\n"
            "/stats - Моя статистика\n\n"
            "Как добавить предметы:\n"
            "Просто отправь сообщение с предметами:\n"
            "• Каждый предмет с новой строки\n"
            "• Или через запятую\n\n"
            "Лимиты:\n"
            "• Максимум 20 предметов\n"
            "• Минимум 2 предмета для генерации\n"
            "• До 10 запросов в минуту"
        )
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений с предметами"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        items = self._parse_items(text)
        
        if not items:
            await update.message.reply_text(
                "❌ Не могу распознать предметы. Попробуй снова!\n"
                "Пример: молоток, гвозди, доски"
            )
            return
        
        added_count = 0
        for item in items:
            if self.db.add_item(user_id, item):
                added_count += 1
        
        current_items = self.db.get_user_items(user_id)
        
        response = f"✅ Добавлено предметов: {added_count}\n\n"
        response += f"📦 Всего предметов: {len(current_items)}\n\n"
        response += "Твой список:\n" + "\n".join(f"• {item}" for item in current_items[:10])
        
        if len(current_items) > 10:
            response += f"\n... и ещё {len(current_items) - 10}"
        
        keyboard = []
        if len(current_items) >= config.MIN_ITEMS_FOR_IDEAS:
            keyboard.append([
                InlineKeyboardButton("🚀 Сгенерировать идеи", callback_data="generate")
            ])
        keyboard.append([
            InlineKeyboardButton("📋 Все предметы", callback_data="show_all"),
            InlineKeyboardButton("🗑️ Очистить", callback_data="clear_confirm")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
    
    def _parse_items(self, text: str):
        """Парсинг предметов из текста"""
        separators = [',', '\n', ';', '•', '-']
        items = [text]
        
        for sep in separators:
            new_items = []
            for item in items:
                new_items.extend(item.split(sep))
            items = new_items
        
        cleaned = []
        for item in items:
            item = item.strip().lower()
            item = re.sub(r'^\d+\.?\s*', '', item)
            if item and len(item) > 1:
                cleaned.append(item)
        
        return list(dict.fromkeys(cleaned))
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline-кнопки"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data
        
        if data == "generate":
            await self._handle_generate(query, user_id)
        elif data == "show_all":
            await self._handle_show_all(query, user_id)
        elif data == "clear_confirm":
            await self._handle_clear_confirm(query)
        elif data == "clear_yes":
            await self._handle_clear_execute(query, user_id)
        elif data == "clear_no":
            await query.edit_message_text("Отменено ✅")
        elif data == "stats":
            await self._handle_stats(query, user_id)
        elif data == "help":
            await self._handle_help_callback(query)
        elif data.startswith("delete_"):
            item = data.replace("delete_", "")
            await self._handle_delete_item(query, user_id, item)
    
    async def _handle_generate(self, query, user_id: int):
        """Генерация идей"""
        allowed, remaining = self.db.check_rate_limit(
            user_id, 
            window_seconds=60, 
            max_actions=config.MAX_REQUESTS_PER_MINUTE
        )
        
        if not allowed:
            await query.edit_message_text(
                "⚠️ Превышен лимит запросов!\n\n"
                "Подожди минутку перед следующей генерацией 🕐"
            )
            return
        
        items = self.db.get_user_items(user_id)
        
        if len(items) < config.MIN_ITEMS_FOR_IDEAS:
            await query.edit_message_text(
                f"❌ Нужно минимум {config.MIN_ITEMS_FOR_IDEAS} предмета для генерации идей!\n"
                f"У тебя сейчас: {len(items)}"
            )
            return
        
        await query.edit_message_text(
            "🔮 Генерирую идеи...\n\n"
            f"Предметы: {', '.join(items[:5])}{'...' if len(items) > 5 else ''}\n"
            "⏳ Это займёт 5-15 секунд..."
        )
        
        result = self.ai.generate_creative_ideas(items, count=min(config.MAX_IDEAS_PER_REQUEST, 5))
        
        if result["success"]:
            ideas_text = result["ideas"]
            self.db.save_generated_ideas(user_id, items, result)
            
            response = f"✨ Креативные идеи для твоих предметов! ✨\n\n{ideas_text}\n\n"
            response += f"📦 Использовано предметов: {len(items)}\n\n"
            response += "💡 Понравились идеи? Попробуй добавить больше предметов!"
        else:
            response = "❌ Произошла ошибка генерации\n\n"
            if "fallback_ideas" in result:
                response += "Вот несколько базовых идей:\n\n" + result["fallback_ideas"]
            else:
                response += f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Ещё идеи", callback_data="generate")],
            [InlineKeyboardButton("📋 Мои предметы", callback_data="show_all")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, part in enumerate(parts):
                if i == 0:
                    await query.edit_message_text(part)
                else:
                    await query.message.reply_text(
                        part,
                        reply_markup=reply_markup if i == len(parts)-1 else None
                    )
        else:
            await query.edit_message_text(response, reply_markup=reply_markup)
    
    async def _handle_show_all(self, query, user_id: int):
        """Показать все предметы"""
        items = self.db.get_user_items(user_id)
        
        if not items:
            await query.edit_message_text("📦 Список предметов пуст!")
            return
        
        response = f"📦 Твои предметы ({len(items)}):\n\n"
        
        keyboard = []
        for item in items[:15]:
            keyboard.append([
                InlineKeyboardButton(f"❌ {item}", callback_data=f"delete_{item}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🚀 Генерировать", callback_data="generate"),
            InlineKeyboardButton("🗑️ Очистить всё", callback_data="clear_confirm")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response + "Нажми на предмет, чтобы удалить его",
            reply_markup=reply_markup
        )
    
    async def _handle_clear_confirm(self, query):
        """Подтверждение очистки"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, очистить", callback_data="clear_yes"),
                InlineKeyboardButton("❌ Нет", callback_data="clear_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚠️ Точно удалить все предметы?\n\nЭто действие нельзя отменить!",
            reply_markup=reply_markup
        )
    
    async def _handle_clear_execute(self, query, user_id: int):
        """Выполнение очистки"""
        self.db.clear_items(user_id)
        await query.edit_message_text(
            "✅ Все предметы удалены!\n\nМожешь добавить новые 📦"
        )
    
    async def _handle_delete_item(self, query, user_id: int, item: str):
        """Удаление конкретного предмета"""
        if self.db.delete_item(user_id, item):
            await query.answer(f"✅ Удалено: {item}")
            await self._handle_show_all(query, user_id)
        else:
            await query.answer("❌ Ошибка удаления")
    
    async def _handle_stats(self, query, user_id: int):
        """Показать статистику пользователя"""
        stats = self.db.get_user_stats(user_id)
        
        response = (
            "📊 Твоя статистика\n\n"
            f"🎯 Всего запросов: {stats['total_requests']}\n"
            f"📦 Активных предметов: {stats['items_count']}\n"
            f"📅 Дата регистрации: {stats['member_since'][:10]}\n\n"
            "💡 Продолжай экспериментировать!"
        )
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="help")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(response, reply_markup=reply_markup)
    
    async def _handle_help_callback(self, query):
        """Помощь через callback"""
        help_text = (
            "📚 Быстрая справка\n\n"
            "Как пользоваться:\n"
            "1️⃣ Отправь предметы\n"
            "2️⃣ Нажми 'Генерировать'\n"
            "3️⃣ Получи идеи!\n\n"
            "Команды:\n"
            "/start /help /myitems /clear /stats\n\n"
            "💡 Больше предметов = больше идей!"
        )
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup)
    
    async def myitems_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /myitems"""
        user_id = update.effective_user.id
        items = self.db.get_user_items(user_id)
        
        if not items:
            await update.message.reply_text(
                "📦 У тебя пока нет предметов!\n\n"
                "Отправь мне список предметов, чтобы начать 🚀"
            )
            return
        
        response = f"📦 Твои предметы ({len(items)}):\n\n"
        response += "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
        
        keyboard = [
            [InlineKeyboardButton("🚀 Генерировать идеи", callback_data="generate")],
            [InlineKeyboardButton("🗑️ Очистить", callback_data="clear_confirm")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /clear"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data="clear_yes"),
                InlineKeyboardButton("❌ Нет", callback_data="clear_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ Удалить все предметы?",
            reply_markup=reply_markup
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        user_id = update.effective_user.id
        stats = self.db.get_user_stats(user_id)
        
        response = (
            "📊 Твоя статистика\n\n"
            f"👤 Пользователь: {update.effective_user.first_name}\n"
            f"🎯 Всего генераций: {stats['total_requests']}\n"
            f"📦 Активных предметов: {stats['items_count']}/{config.MAX_ITEMS_PER_USER}\n"
            f"📅 С нами с: {stats['member_since'][:10]}\n\n"
        )
        response += "🔥 Отличная активность!" if stats['total_requests'] > 10 else "💡 Попробуй ещё!"
        
        await update.message.reply_text(response)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Exception while handling update: {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка!\n\n"
                    "Попробуй ещё раз или свяжись с поддержкой."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")


def main():
    """Запуск бота"""
    if config.TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Установите TELEGRAM_TOKEN в .env файле!")
        return
    
    print("🤖 Запуск Creative Items Bot...")
    print(f"📊 База данных: {config.DATABASE_NAME}")
    print(f"🧠 AI модель: {config.AI_MODEL}")
    print(f"🔗 AI URL: {config.AI_BASE_URL}")
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    bot = CreativeBot()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("myitems", bot.myitems_command))
    application.add_handler(CommandHandler("clear", bot.clear_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_message
    ))
    application.add_error_handler(bot.error_handler)
    
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
