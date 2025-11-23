"""
Texel Try-On Telegram Bot
"""
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from config import config
from database import DatabaseManager
from tryon_engine import TryOnEngine

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация
db = DatabaseManager(config.DATABASE_NAME)
tryon_engine = TryOnEngine(config.RAPIDAPI_KEY)

# Создаём папку для временных файлов
os.makedirs(config.TEMP_DIR, exist_ok=True)


class TexelBot:
    """Основной класс бота"""
    
    def __init__(self):
        self.db = db
        self.tryon = tryon_engine
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        self.db.add_or_update_user(
            user.id, user.username, user.first_name, user.last_name
        )
        
        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Я — **Texel Try-On Bot** 🤖👔\n\n"
            "🔮 Что я умею:\n"
            "• Виртуальная примерка одежды\n"
            "• AI-генерация образов\n"
            "• Мгновенный результат\n\n"
            "📸 Как использовать:\n"
            "1️⃣ Нажми /tryon\n"
            "2️⃣ Отправь фото человека\n"
            "3️⃣ Отправь фото одежды\n"
            "4️⃣ Получи результат!\n\n"
            "Попробуй прямо сейчас! 👇"
        )
        
        keyboard = [
            [InlineKeyboardButton("👔 Начать примерку", callback_data="start_tryon")],
            [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def tryon_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /tryon"""
        user_id = update.effective_user.id
        
        # Проверка лимита
        allowed, remaining = self.db.check_rate_limit(
            user_id, 
            window_hours=24, 
            max_actions=config.MAX_REQUESTS_PER_DAY
        )
        
        if not allowed:
            await update.message.reply_text(
                "⚠️ Превышен дневной лимит!\n\n"
                "Попробуй завтра 🕐"
            )
            return
        
        help_text = (
            "👔 **Виртуальная примерка**\n\n"
            "📸 Шаг 1: Отправь фото человека\n"
            "• В полный рост\n"
            "• Чёткое изображение\n"
            "• Хорошее освещение\n\n"
            f"💫 Осталось попыток сегодня: {remaining}"
        )
        
        context.user_data['awaiting_person_photo'] = True
        
        keyboard = [
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel_tryon")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка фотографий"""
        user_id = update.effective_user.id
        photo = update.message.photo[-1]
        
        file = await photo.get_file()
        
        if context.user_data.get('awaiting_person_photo'):
            file_path = os.path.join(config.TEMP_DIR, f"person_{user_id}.jpg")
            await file.download_to_drive(file_path)
            
            context.user_data['person_photo_path'] = file_path
            context.user_data['person_photo_id'] = photo.file_id
            context.user_data['awaiting_person_photo'] = False
            context.user_data['awaiting_garment_photo'] = True
            
            keyboard = [
                [InlineKeyboardButton("❌ Отменить", callback_data="cancel_tryon")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "✅ Фото человека получено!\n\n"
                "📸 Шаг 2: Отправь фото одежды 👕\n"
                "• Одежда на однотонном фоне\n"
                "• Чёткое изображение",
                reply_markup=reply_markup
            )
        
        elif context.user_data.get('awaiting_garment_photo'):
            file_path = os.path.join(config.TEMP_DIR, f"garment_{user_id}.jpg")
            await file.download_to_drive(file_path)
            
            context.user_data['garment_photo_path'] = file_path
            context.user_data['garment_photo_id'] = photo.file_id
            context.user_data['awaiting_garment_photo'] = False
            
            await update.message.reply_text(
                "🔮 **Генерирую примерку...**\n\n"
                "⏳ Это займёт 30-90 секунд\n"
                "Пожалуйста, подожди...",
                parse_mode='Markdown'
            )
            
            # Генерация через Texel API
            result = self.tryon.generate_tryon(
                person_image_path=context.user_data['person_photo_path'],
                garment_image_path=context.user_data['garment_photo_path'],
                category="upper_body"
            )
            
            if result["success"]:
                with open(result["output_path"], 'rb') as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption=(
                            "✨ **Вот результат!**\n\n"
                            "Как тебе образ? 😊\n\n"
                            "Хочешь примерить ещё? /tryon"
                        ),
                        parse_mode='Markdown'
                    )
                
                # Сохраняем в БД
                self.db.save_tryon(
                    user_id,
                    context.user_data['person_photo_id'],
                    context.user_data['garment_photo_id'],
                    "upper_body",
                    success=True
                )
                
                # Удаляем временные файлы
                os.remove(context.user_data['person_photo_path'])
                os.remove(context.user_data['garment_photo_path'])
                os.remove(result["output_path"])
            else:
                await update.message.reply_text(
                    f"❌ **Ошибка генерации**\n\n"
                    f"Причина: {result.get('error', 'Неизвестная ошибка')}\n\n"
                    f"Попробуй:\n"
                    f"• Другие фото\n"
                    f"• Лучшее качество\n"
                    f"• /tryon снова",
                    parse_mode='Markdown'
                )
                
                self.db.save_tryon(
                    user_id,
                    context.user_data['person_photo_id'],
                    context.user_data['garment_photo_id'],
                    "upper_body",
                    success=False
                )
            
            context.user_data.clear()
        else:
            await update.message.reply_text(
                "📸 Сначала начни примерку командой /tryon"
            )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data == "start_tryon":
            context.user_data['awaiting_person_photo'] = True
            
            keyboard = [
                [InlineKeyboardButton("❌ Отменить", callback_data="cancel_tryon")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👔 **Виртуальная примерка**\n\n"
                "📸 Отправь фото человека (в полный рост)",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        elif data == "cancel_tryon":
            context.user_data.clear()
            await query.edit_message_text("❌ Примерка отменена\n\nДля новой попытки: /tryon")
        
        elif data == "stats":
            stats = self.db.get_user_stats(user_id)
            
            response = (
                "📊 **Твоя статистика**\n\n"
                f"👤 Пользователь: {query.from_user.first_name}\n"
                f"👔 Всего примерок: {stats['total_tryons']}\n"
                f"📅 С нами с: {stats['member_since'][:10] if stats['member_since'] else 'сегодня'}\n\n"
                "🔥 Продолжай экспериментировать!"
            )
            
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                response,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        elif data == "help":
            help_text = (
                "ℹ️ **Помощь**\n\n"
                "**Команды:**\n"
                "/start - Главное меню\n"
                "/tryon - Начать примерку\n"
                "/stats - Статистика\n\n"
                "**Советы:**\n"
                "• Используй чёткие фото\n"
                "• Хорошее освещение\n"
                "• Одежда на однотонном фоне\n\n"
                "**Лимиты:**\n"
                f"• {config.MAX_REQUESTS_PER_DAY} примерок в день"
            )
            
            keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                help_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        elif data == "back_to_start":
            await self.start_command(query, context)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        user_id = update.effective_user.id
        stats = self.db.get_user_stats(user_id)
        
        response = (
            "📊 **Твоя статистика**\n\n"
            f"👤 {update.effective_user.first_name}\n"
            f"👔 Всего примерок: {stats['total_tryons']}\n"
            f"📅 С нами с: {stats['member_since'][:10] if stats['member_since'] else 'сегодня'}"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Exception: {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка!\n\nПопробуй ещё раз или /start"
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")


def main():
    """Запуск бота"""
    if config.TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Установите TELEGRAM_TOKEN в .env!")
        return
    
    if config.RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY_HERE":
        print("❌ ОШИБКА: Установите RAPIDAPI_KEY в .env!")
        return
    
    print("🤖 Запуск Texel Try-On Bot...")
    print(f"📊 База данных: {config.DATABASE_NAME}")
    
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    bot = TexelBot()
    
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("tryon", bot.tryon_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
    application.add_error_handler(bot.error_handler)
    
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
