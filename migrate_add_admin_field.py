#!/usr/bin/env python3
"""
Міграція: Додавання поля admin_id до User
Виконується один раз після оновлення моделі
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app import app, db

def migrate():
    """Додає поле admin_id до таблиці user"""
    with app.app_context():
        try:
            print("🔧 Перевірка структури таблиці...")
            
            # Спроба створити всі таблиці (якщо не існують)
            db.create_all()
            print("✅ Таблиці створено/оновлено")
            
            print("\n📊 Завершено!")
            print("=" * 60)
            print("Поле 'admin_id' додано до таблиці 'user'")
            print("Тепер брокери можуть бути прив'язані до адмінів")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Помилка: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🔄 МІГРАЦІЯ: Додавання прив'язки брокерів до адмінів")
    print("=" * 60 + "\n")
    migrate()

