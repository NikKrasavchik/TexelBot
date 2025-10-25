"""
AI движок для генерации креативных идей
Использует OpenAI GPT-4
"""
import json
from typing import List, Dict, Optional
from openai import OpenAI
from config import config, AI_PROMPTS
import logging

logger = logging.getLogger(__name__)

class AIEngine:
    """Движок для работы с OpenAI GPT-4"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key)
        self.model = config.AI_MODEL
        self.temperature = config.AI_TEMPERATURE
        self.max_tokens = config.MAX_TOKENS
    
    def generate_creative_ideas(self, items: List[str], 
                               count: int = 5) -> Dict[str, any]:
        """
        Генерация креативных идей на основе списка предметов
        
        Args:
            items: список предметов
            count: количество идей для генерации
            
        Returns:
            Dict с идеями и метаданными
        """
        try:
            # Формируем промпт
            items_str = ", ".join(items)
            prompt = AI_PROMPTS["creative_ideas"].format(
                items=items_str, 
                count=count
            )
            
            # Вызываем API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "Ты — эксперт по DIY-проектам и креативному мышлению. "
                                 "Твоя задача — вдохновлять людей создавать интересные вещи."
                    },
                    {"role": "user", "content": prompt}
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
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации идей: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_ideas": self._generate_fallback_ideas(items)
            }
    
    def _generate_fallback_ideas(self, items: List[str]) -> str:
        """Запасные идеи при сбое API"""
        fallback_templates = [
            f"🎨 **Креативная композиция** 🟢\\n"
            f"📝 *Что получится*: арт-объект из {items} и {items if len(items) > 1 else 'других материалов'}\\n"
            f"⚙️ *Как сделать*: соедини предметы креативным образом, добавь краски\\n"
            f"⏱️ *Время*: 20-30 минут",
            
            f"🛠️ **Функциональное устройство** 🟡\\n"
            f"📝 *Что получится*: полезный гаджет для дома\\n"
            f"⚙️ *Как сделать*: используй {items} как основу, закрепи остальное\\n"
            f"⏱️ *Время*: 1-2 часа",
            
            f"🎁 **Оригинальный подарок** 🟢\\n"
            f"📝 *Что получится*: уникальная вещь ручной работы\\n"
            f"⚙️ *Как сделать*: объедини все предметы в единую композицию\\n"
            f"⏱️ *Время*: 30-40 минут"
        ]
        
        return "\\n\\n".join(fallback_templates[:3])
