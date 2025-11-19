#!/usr/bin/env python3
"""
Скрипт для перевірки та скидання пароля користувача
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def check_password(username, test_password):
    """Перевіряє пароль користувача"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувача '{username}' не знайдено")
            return False
        
        print(f"🔍 Перевірка пароля для користувача: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   ID: {user.id}")
        print(f"   Роль: {user.role}")
        print(f"   Активний: {'✅' if user.is_active else '❌'}")
        print(f"   Заблокований: {'🔒 Так' if user.is_account_locked() else '✅ Ні'}")
        print(f"   Лічильник спроб: {user.login_attempts}")
        print(f"\n🔑 Перевірка пароля: '{test_password}'")
        
        if user.check_password(test_password):
            print("✅ Пароль правильний!")
            return True
        else:
            print("❌ Пароль неправильний!")
            print(f"\n💡 Очікуваний пароль для anton_admin: sfajerfe234ewqf#")
            return False

def reset_password(username, new_password):
    """Скидає пароль користувача"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувача '{username}' не знайдено")
            return False
        
        print(f"🔄 Скидання пароля для користувача: {user.username}")
        user.set_password(new_password)
        user.unlock_account()  # Також розблоковуємо акаунт
        db.session.commit()
        
        print(f"✅ Пароль успішно змінено!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Новий пароль: {new_password}")
        print(f"   Акаунт розблоковано")
        
        return True

if __name__ == "__main__":
    print("🔐 Перевірка та скидання пароля користувача")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        username = sys.argv[1]
        
        if len(sys.argv) > 2:
            # Скидання пароля
            new_password = sys.argv[2]
            reset_password(username, new_password)
        else:
            # Перевірка пароля
            expected_password = 'sfajerfe234ewqf#' if username == 'anton_admin' else None
            if expected_password:
                check_password(username, expected_password)
            else:
                print(f"⚠️  Для перевірки пароля введіть: python {sys.argv[0]} {username} <пароль>")
    else:
        # Інтерактивний режим
        username = input("Введіть ім'я користувача: ").strip()
        if username:
            if username == 'anton_admin':
                test_password = 'sfajerfe234ewqf#'
                print(f"\n🔍 Перевіряю очікуваний пароль для {username}...")
                if check_password(username, test_password):
                    print("\n✅ Пароль правильний! Проблема може бути в іншому.")
                else:
                    print(f"\n❌ Пароль неправильний. Скинути пароль на '{test_password}'? (y/N): ", end='')
                    response = input().lower()
                    if response == 'y':
                        reset_password(username, test_password)
            else:
                print(f"⚠️  Для користувача {username} потрібно вказати пароль вручну")
                print(f"   Використання: python {sys.argv[0]} {username} <пароль>")

