"""
Модуль управления базой данных
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from contextlib import contextmanager
import threading

class DatabaseManager:
    """Менеджер базы данных с поддержкой многопоточности"""
    
    def __init__(self, db_name: str = "creative_bot.db"):
        self.db_name = db_name
        self.local = threading.local()
        self.setup()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для безопасной работы с БД"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        try:
            yield self.local.conn
        except Exception as e:
            self.local.conn.rollback()
            raise e
        else:
            self.local.conn.commit()
    
    def setup(self):
        """Создание таблиц БД"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_requests INTEGER DEFAULT 0,
                    is_blocked BOOLEAN DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_name TEXT NOT NULL,
                    category TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_deleted BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_ideas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    items_used TEXT NOT NULL,
                    ideas_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            conn.commit()
    
    def add_or_update_user(self, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None):
        """Добавление или обновление пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_activity = CURRENT_TIMESTAMP
            """, (user_id, username, first_name, last_name))
    
    def add_item(self, user_id: int, item_name: str, category: str = None) -> bool:
        """Добавление предмета пользователю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM user_items 
                WHERE user_id = ? AND is_deleted = 0
            """, (user_id,))
            count = cursor.fetchone()
            
            if count >= 20:
                return False
            
            cursor.execute("""
                INSERT INTO user_items (user_id, item_name, category)
                VALUES (?, ?, ?)
            """, (user_id, item_name.lower().strip(), category))
            return True
    
    def get_user_items(self, user_id: int) -> List[str]:
        """Получение всех предметов пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_name FROM user_items
                WHERE user_id = ? AND is_deleted = 0
                ORDER BY added_at DESC
            """, (user_id,))
            return [row for row in cursor.fetchall()]
    
    def delete_item(self, user_id: int, item_name: str) -> bool:
        """Удаление предмета"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_items 
                SET is_deleted = 1
                WHERE user_id = ? AND item_name = ? AND is_deleted = 0
            """, (user_id, item_name.lower().strip()))
            return cursor.rowcount > 0
    
    def clear_items(self, user_id: int):
        """Очистка всех предметов пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_items 
                SET is_deleted = 1
                WHERE user_id = ? AND is_deleted = 0
            """, (user_id,))
    
    def save_generated_ideas(self, user_id: int, items: List[str], ideas: Dict) -> int:
        """Сохранение сгенерированных идей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generated_ideas (user_id, items_used, ideas_json)
                VALUES (?, ?, ?)
            """, (user_id, json.dumps(items, ensure_ascii=False), 
                  json.dumps(ideas, ensure_ascii=False)))
            return cursor.lastrowid
    
    def check_rate_limit(self, user_id: int, window_seconds: int = 60, 
                        max_actions: int = 10) -> Tuple[bool, int]:
        """Проверка лимита запросов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_actions
                WHERE user_id = ? AND timestamp > ?
            """, (user_id, cutoff_time))
            
            count = cursor.fetchone()
            remaining = max(0, max_actions - count)
            
            if count < max_actions:
                cursor.execute("""
                    INSERT INTO user_actions (user_id, action_type)
                    VALUES (?, 'generate_ideas')
                """, (user_id,))
                return True, remaining
            
            return False, 0
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM generated_ideas WHERE user_id = ?
            """, (user_id,))
            total_requests = cursor.fetchone()
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_items 
                WHERE user_id = ? AND is_deleted = 0
            """, (user_id,))
            items_count = cursor.fetchone()
            
            cursor.execute("""
                SELECT created_at FROM users WHERE user_id = ?
            """, (user_id,))
            created_at = cursor.fetchone()
            
            return {
                "total_requests": total_requests,
                "items_count": items_count,
                "member_since": created_at
            }
