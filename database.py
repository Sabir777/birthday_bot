"""Модуль для работы с базой данных SQLite"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple


class Database:
    """Класс для управления базой данных коллег"""

    def __init__(self, db_path: str = "birthdays.db"):
        self.db_path = db_path
        self.create_tables()

    def create_tables(self):
        """Создание таблиц в базе данных"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS colleagues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    birth_month INTEGER NOT NULL,
                    birth_day INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_settings (
                    id INTEGER PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    notifications_enabled BOOLEAN DEFAULT 1
                )
            """)
            conn.commit()

    def add_colleague(self, name: str, birth_date: str) -> bool:
        """
        Добавить коллегу в базу данных
        
        Args:
            name: Имя коллеги
            birth_date: Дата рождения в формате DD.MM
            
        Returns:
            True если успешно, False если ошибка
        """
        try:
            day, month = map(int, birth_date.split("."))
            if not (1 <= day <= 31 and 1 <= month <= 12):
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO colleagues (name, birth_month, birth_day) VALUES (?, ?, ?)",
                    (name, month, day)
                )
                conn.commit()
            return True
        except (ValueError, sqlite3.Error):
            return False

    def get_colleagues_by_date(self, month: int, day: int) -> List[Tuple[int, str]]:
        """
        Получить всех коллег, у которых день рождения в указанную дату
        
        Args:
            month: Месяц
            day: День
            
        Returns:
            Список кортежей (id, имя)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name FROM colleagues WHERE birth_month = ? AND birth_day = ?",
                (month, day)
            )
            return cursor.fetchall()

    def get_all_colleagues(self) -> List[Tuple[int, str, int, int]]:
        """
        Получить всех коллег
        
        Returns:
            Список кортежей (id, имя, месяц, день)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, birth_month, birth_day FROM colleagues ORDER BY birth_month, birth_day"
            )
            return cursor.fetchall()

    def delete_colleague(self, colleague_id: int) -> bool:
        """
        Удалить коллегу по ID
        
        Args:
            colleague_id: ID коллеги
            
        Returns:
            True если успешно, False если не найден
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM colleagues WHERE id = ?", (colleague_id,))
            return cursor.rowcount > 0

    def get_colleague_by_id(self, colleague_id: int) -> Optional[Tuple[int, str, int, int]]:
        """
        Получить коллегу по ID
        
        Args:
            colleague_id: ID коллеги
            
        Returns:
            Кортеж (id, имя, месяц, день) или None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, birth_month, birth_day FROM colleagues WHERE id = ?",
                (colleague_id,)
            )
            return cursor.fetchone()

    def save_chat_settings(self, chat_id: str, notifications_enabled: bool = True):
        """Сохранить настройки чата"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO chat_settings (id, chat_id, notifications_enabled) 
                   VALUES (1, ?, ?)""",
                (chat_id, notifications_enabled)
            )
            conn.commit()

    def get_chat_settings(self) -> Optional[Tuple[int, str, bool]]:
        """Получить настройки чата"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, chat_id, notifications_enabled FROM chat_settings WHERE id = 1")
            return cursor.fetchone()
