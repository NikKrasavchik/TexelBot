"""
AI движок для работы с локальным Ollama (без OpenAI-клиента)
"""
import logging
from typing import List, Dict

import requests

from config import config

logger = logging.getLogger("ai_engine")


class AIEngine:
    """Движок для генерации креативных идей через Ollama"""

    def __init__(self):
        # Берём базовый URL и модель из конфига
        self.base_url = config.AI_BASE_URL  # ожидаем http://localhost:11434 или http://localhost:11434/api
        self.model = config.AI_MODEL
        self.temperature = config.AI_TEMPERATURE
        self.max_tokens = config.MAX_TOKENS

        # Нормализуем base_url до вида http://localhost:11434 (без /v1)
        if self.base_url.endswith("/v1"):
            self.base_url = self.base_url[:-3]
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]

        self.chat_url = f"{self.base_url}/api/chat"

    def generate_creative_ideas(self, items: List[str], count: int = 5) -> Dict:
        """
        Генерация креативных идей через Ollama /api/chat

        Args:
            items: список предметов
            count: количество идей
        """
        try:
            items_str = ", ".join(items)
            prompt = f"""Пользователь предоставил следующие предметы: {items_str}.

Твоя задача — предложить {count} УНИКАЛЬНЫХ и ПРАКТИЧНЫХ идей того, что можно создать из этих предметов.

Требования к идеям:
1. Каждая идея должна быть РЕАЛЬНО выполнимой.
2. Укажи уровень сложности (🟢 Легко / 🟡 Средне / 🔴 Сложно).
3. Добавь эмодзи для визуализации.
4. Кратко опиши процесс (1-2 предложения).
5. Укажи примерное время создания.

Формат ответа:

[Эмодзи] **Название проекта** [Сложность]
📝 Что получится: краткое описание
⚙️ Как сделать: краткая инструкция
⏱️ Время: примерное время

Будь креативным, но реалистичным!"""

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты — эксперт по DIY-проектам с 15-летним опытом. "
                                   "Твоя задача — вдохновлять людей создавать интересные вещи."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
                "stream": False,
            }

            resp = requests.post(self.chat_url, json=payload, timeout=120)
            if resp.status_code != 200:
                logger.error(f"Ollama API error {resp.status_code}: {resp.text[:200]!r}")
                return {
                    "success": False,
                    "error": f"Ollama API error {resp.status_code}",
                    "fallback_ideas": self._generate_fallback_ideas(items),
                }

            data = resp.json()
            # Формат ответа Ollama /api/chat: {"message": {"role": "...", "content": "..."}, ...}
            if "message" in data and "content" in data["message"]:
                ideas_text = data["message"]["content"]
            else:
                # На всякий случай
                ideas_text = str(data)

            return {
                "success": True,
                "ideas": ideas_text,
                "items_used": items,
                "model": self.model,
                "provider": "ollama",
            }

        except Exception as e:
            logger.error(f"Ошибка генерации идей через Ollama: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_ideas": self._generate_fallback_ideas(items),
            }

    def _generate_fallback_ideas(self, items: List[str]) -> str:
        item_list = ", ".join(items) if items else "несколько предметов"
        return f"""🎨 **Креативная композиция** 🟢
📝 Что получится: арт-объект из {item_list} и {item_list}
⚙️ Как сделать: соедини предметы креативным образом, добавь краски
⏱️ Время: 20-30 минут

🛠️ **Функциональное устройство** 🟡
📝 Что получится: полезный гаджет для дома
⚙️ Как сделать: используй {item_list} как основу, закрепи остальное
⏱️ Время: 1-2 часа

🎁 **Оригинальный подарок** 🟢
📝 Что получится: уникальная вещь ручной работы
⚙️ Как сделать: объедини все предметы в единую композицию
⏱️ Время: 30-40 минут"""
