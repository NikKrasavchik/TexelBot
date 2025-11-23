"""
Модуль управления базой данных
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Tuple
from contextlib import contextmanager
import threading

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, db_name: str = "texel_bot.db"):
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
                    total_tryons INTEGER DEFAULT 0,
                    is_blocked BOOLEAN DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tryons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    person_photo_id TEXT,
                    garment_photo_id TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT 1,
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
    
    def save_tryon(self, user_id: int, person_photo_id: str, 
                   garment_photo_id: str, category: str, success: bool = True):
        """Сохранение примерки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tryons (user_id, person_photo_id, garment_photo_id, category, success)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, person_photo_id, garment_photo_id, category, success))
            
            cursor.execute("""
                UPDATE users SET total_tryons = total_tryons + 1
                WHERE user_id = ?
            """, (user_id,))
    
    def check_rate_limit(self, user_id: int, window_hours: int = 24, 
                        max_actions: int = 50) -> Tuple[bool, int]:
        """Проверка лимита запросов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_time = datetime.now() - timedelta(hours=window_hours)
            
            cursor.execute("""
                SELECT COUNT(*) FROM user_actions
                WHERE user_id = ? AND timestamp > ?
            """, (user_id, cutoff_time))
            
            count = cursor.fetchone()
            remaining = max(0, max_actions - count)
            
            if count < max_actions:
                cursor.execute("""
                    INSERT INTO user_actions (user_id, action_type)
                    VALUES (?, 'tryon_request')
                """, (user_id,))
                return True, remaining
            
            return False, 0
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получение статистики пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT total_tryons, created_at FROM users WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "total_tryons": row,
                    "member_since": row
                }
            return {"total_tryons": 0, "member_since": None}
