#!/usr/bin/env python3
"""
Міграція для додавання таблиці коментарів
"""
import os
import sys
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

# Додаємо поточну директорію до шляху
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate():
    """Створює таблицю коментарів"""
    with app.app_context():
        try:
            # Перевіряємо, чи існує таблиця
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'comment' in existing_tables:
                print("✅ Таблиця 'comment' вже існує")
                return
            
            # Створюємо таблицю
            print("🔄 Створення таблиці 'comment'...")
            db.create_all()
            
            # Перевіряємо, чи створилася таблиця
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'comment' in tables:
                print("✅ Таблиця 'comment' успішно створена")
                
                # Виводимо структуру таблиці
                columns = inspector.get_columns('comment')
                print("\n📋 Структура таблиці 'comment':")
                for col in columns:
                    print(f"   - {col['name']}: {col['type']}")
            else:
                print("⚠️ Таблиця 'comment' не створена")
                
        except Exception as e:
            print(f"❌ Помилка міграції: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate()

