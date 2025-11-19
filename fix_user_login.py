#!/usr/bin/env python3
"""
Скрипт для повного виправлення проблем з логіном користувача
- Розблоковує акаунт
- Скидає лічильник спроб
- Перевіряє/скидає пароль
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def fix_user_login(username, reset_password=None):
    """Повне виправлення проблем з логіном"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувача '{username}' не знайдено")
            return False
        
        print("=" * 70)
        print(f"🔧 ВИПРАВЛЕННЯ ПРОБЛЕМ З ЛОГІНОМ ДЛЯ: {user.username}")
        print("=" * 70)
        
        # Поточний стан
        print("\n📊 ПОТОЧНИЙ СТАН:")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Роль: {user.role}")
        print(f"   Активний: {'✅' if user.is_active else '❌'}")
        print(f"   Заблокований: {'🔒 Так' if user.is_account_locked() else '✅ Ні'}")
        print(f"   Лічильник спроб: {user.login_attempts}")
        print(f"   Блокування до: {user.locked_until.strftime('%Y-%m-%d %H:%M:%S') if user.locked_until else 'Немає'}")
        
        # Виправлення
        print("\n🔧 ВИПРАВЛЕННЯ:")
        
        # 1. Розблоковуємо акаунт
        if user.locked_until:
            print("   1. ✅ Розблоковую акаунт...")
            user.unlock_account()
        else:
            print("   1. ℹ️  Акаунт не заблокований")
        
        # 2. Скидаємо лічильник спроб
        if user.login_attempts > 0:
            print(f"   2. ✅ Скидаю лічильник спроб (було: {user.login_attempts})...")
            user.login_attempts = 0
        else:
            print("   2. ℹ️  Лічильник спроб вже на нулі")
        
        # 3. Перевіряємо/скидаємо пароль
        expected_password = 'sfajerfe234ewqf#' if username == 'anton_admin' else reset_password
        
        if expected_password:
            if user.check_password(expected_password):
                print(f"   3. ✅ Пароль правильний")
            else:
                print(f"   3. ⚠️  Пароль неправильний, скидаю на правильний...")
                user.set_password(expected_password)
                print(f"      ✅ Пароль встановлено: {expected_password}")
        else:
            print("   3. ℹ️  Пароль не перевіряється (не вказано очікуваний)")
        
        # 4. Перевіряємо, чи активний
        if not user.is_active:
            print("   4. ⚠️  Акаунт неактивний, активую...")
            user.is_active = True
        else:
            print("   4. ✅ Акаунт активний")
        
        # Зберігаємо зміни
        db.session.commit()
        
        # Фінальний стан
        print("\n✅ ВИПРАВЛЕННЯ ЗАВЕРШЕНО!")
        print("\n📊 НОВИЙ СТАН:")
        print(f"   Заблокований: {'🔒 Так' if user.is_account_locked() else '✅ Ні'}")
        print(f"   Лічильник спроб: {user.login_attempts}")
        print(f"   Активний: {'✅' if user.is_active else '❌'}")
        
        if expected_password:
            print(f"\n🔑 ДАНІ ДЛЯ ВХОДУ:")
            print(f"   Username: {user.username}")
            print(f"   Password: {expected_password}")
        
        print("\n" + "=" * 70)
        print("💡 Якщо проблема залишається:")
        print("   - Перевірте, чи використовуєте правильний URL (production vs local)")
        print("   - Перевірте, чи не перевищено rate limit (10 спроб/хвилину)")
        print("   - Спробуйте очистити cookies браузера")
        print("=" * 70)
        
        return True

if __name__ == "__main__":
    print("🔧 Виправлення проблем з логіном")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        username = sys.argv[1]
        reset_password = sys.argv[2] if len(sys.argv) > 2 else None
        fix_user_login(username, reset_password)
    else:
        username = input("Введіть ім'я користувача: ").strip()
        if username:
            if username == 'anton_admin':
                fix_user_login(username, 'sfajerfe234ewqf#')
            else:
                print(f"⚠️  Для інших користувачів вкажіть пароль:")
                print(f"   Використання: python {sys.argv[0]} {username} <пароль>")
                password = input("Пароль (Enter для пропуску): ").strip()
                if password:
                    fix_user_login(username, password)
                else:
                    fix_user_login(username)

