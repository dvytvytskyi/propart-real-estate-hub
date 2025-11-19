#!/usr/bin/env python3
"""
Скрипт для розблокування користувача після невдалих спроб логіну
Використання: python unlock_user.py
"""

import sys
import os
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

# Додаємо поточну директорію до шляху для імпорту app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def unlock_user(username):
    """Розблоковує користувача за username"""
    with app.app_context():
        # Шукаємо користувача (спробуємо різні варіанти імені)
        user = None
        
        # Спочатку шукаємо точне співпадіння
        user = User.query.filter_by(username=username).first()
        
        # Якщо не знайдено, шукаємо без урахування регістру
        if not user:
            users = User.query.all()
            for u in users:
                if u.username.lower() == username.lower():
                    user = u
                    break
        
        if not user:
            print(f"❌ Користувача з ім'ям '{username}' не знайдено")
            print("\n📋 Доступні користувачі:")
            all_users = User.query.all()
            if all_users:
                print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Заблоковано'}")
                print("-" * 70)
                for u in all_users:
                    locked = "✅ Так" if (u.locked_until and u.is_account_locked()) else "❌ Ні"
                    print(f"{u.id:<5} {u.username:<20} {u.email:<30} {locked}")
            else:
                print("  (немає користувачів в базі)")
            return False
        
        # Перевіряємо, чи заблокований
        if not user.locked_until:
            print(f"✅ Користувач '{user.username}' не заблокований")
            print(f"   Лічильник спроб: {user.login_attempts}")
            return True
        
        # Розблоковуємо
        user.unlock_account()
        db.session.commit()
        
        print(f"✅ Користувач '{user.username}' успішно розблокований!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Лічильник спроб скинуто: {user.login_attempts}")
        print(f"   Блокування до: {user.locked_until if user.locked_until else 'Немає'}")
        
        return True

if __name__ == "__main__":
    print("🔓 Розблокування користувача")
    print("=" * 50)
    
    # Якщо передано аргумент командного рядка
    if len(sys.argv) > 1:
        username = sys.argv[1]
        unlock_user(username)
    else:
        # Інтерактивний режим
        username = input("Введіть ім'я користувача для розблокування: ").strip()
        if username:
            unlock_user(username)
        else:
            print("❌ Ім'я користувача не може бути порожнім")

