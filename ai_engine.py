"""
AI движок для работы с Ollama
"""
import logging
from typing import List, Dict
from openai import OpenAI
from config import config

logger = logging.getLogger(__name__)

class AIEngine:
    """Движок для работы с Ollama"""
    
    def __init__(self):
        """Инициализация клиента Ollama"""
        # Ollama использует OpenAI-совместимый API
        self.client = OpenAI(
            base_url=config.AI_BASE_URL,
            api_key="ollama"  # Для Ollama ключ не нужен, но библиотека требует
        )
        self.model = config.AI_MODEL
        self.temperature = config.AI_TEMPERATURE
        self.max_tokens = config.MAX_TOKENS
    
    def generate_creative_ideas(self, items: List[str], count: int = 5) -> Dict:
        """
        Генерация креативных идей через Ollama
        
        Args:
            items: список предметов
            count: количество идей
            
        Returns:
            Dict с идеями и метаданными
        """
        try:
            items_str = ", ".join(items)
            
            prompt = f"""Пользователь предоставил следующие предметы: {items_str}

Твоя задача — предложить {count} УНИКАЛЬНЫХ и ПРАКТИЧНЫХ идей того, что можно создать из этих предметов.

Требования к идеям:
1. Каждая идея должна быть РЕАЛЬНО выполнимой
2. Укажи уровень сложности (🟢 Легко / 🟡 Средне / 🔴 Сложно)
3. Добавь эмодзи для визуализации
4. Кратко опиши процесс (1-2 предложения)
5. Укажи примерное время создания

Формат ответа:

[Эмодзи] **Название проекта** [Сложность]
📝 Что получится: краткое описание
⚙️ Как сделать: краткая инструкция
⏱️ Время: примерное время

Будь креативным, но реалистичным!"""
            
            # Вызов Ollama через OpenAI-совместимый API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты — эксперт по DIY-проектам с 15-летним опытом. Твоя задача — вдохновлять людей создавать интересные вещи."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            ideas_text = response.choices.message.content
            
            return {
                "success": True,
                "ideas": ideas_text,
                "items_used": items,
                "model": self.model,
                "provider": "ollama"
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации идей через Ollama: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_ideas": self._generate_fallback_ideas(items)
            }
    
    def _generate_fallback_ideas(self, items: List[str]) -> str:
        """Запасные идеи при сбое"""
        item1 = items if len(items) > 0 else "предметы"
        item2 = items if len(items) > 1 else "материалы"
        
        return f"""🎨 **Креативная композиция** 🟢
📝 Что получится: арт-объект из {item1} и {item2}
⚙️ Как сделать: соедини предметы креативным образом, добавь краски
⏱️ Время: 20-30 минут

🛠️ **Функциональное устройство** 🟡
📝 Что получится: полезный гаджет для дома
⚙️ Как сделать: используй {item1} как основу, закрепи остальное
⏱️ Время: 1-2 часа

🎁 **Оригинальный подарок** 🟢
📝 Что получится: уникальная вещь ручной работы
⚙️ Как сделать: объедини все предметы в единую композицию
⏱️ Время: 30-40 минут"""
