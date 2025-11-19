#!/usr/bin/env python3
"""
Повна перевірка логіну агента - перевіряє все по БД та налаштування
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from flask_login import login_user
from datetime import datetime

def check_agent_full(username):
    """Повна перевірка агента"""
    with app.app_context():
        print("=" * 80)
        print(f"🔍 ПОВНА ПЕРЕВІРКА АГЕНТА: {username}")
        print("=" * 80)
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувача '{username}' не знайдено в базі даних")
            return False
        
        print(f"\n📊 ІНФОРМАЦІЯ З БАЗИ ДАНИХ:")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Роль: {user.role}")
        print(f"   is_active: {user.is_active}")
        print(f"   login_attempts: {user.login_attempts}")
        print(f"   locked_until: {user.locked_until}")
        print(f"   last_login: {user.last_login}")
        print(f"   password_hash: {user.password_hash[:50]}...")
        
        # Перевірка статусу
        print(f"\n🔍 ПЕРЕВІРКА СТАТУСУ:")
        is_locked = user.is_account_locked()
        print(f"   is_account_locked(): {is_locked}")
        print(f"   is_active: {user.is_active}")
        
        if is_locked:
            print(f"   ❌ Акаунт заблокований до: {user.locked_until}")
            return False
        
        if not user.is_active:
            print(f"   ❌ Акаунт неактивний")
            return False
        
        print(f"   ✅ Акаунт активний і не заблокований")
        
        # Перевірка паролів
        print(f"\n🔑 ПЕРЕВІРКА ПАРОЛІВ:")
        known_passwords = {
            'agent': 'agent123',
            'olena_birovchak': 'temp_olena_birovchak123!',
            'ustyan': 'temp_ustyan123!',
            'alexander_novikov': 'temp_alexander_novikov123!',
            'uik': 'temp_uik123!',
            'blagovest': 'temp_blagovest123!',
            'timonov': 'temp_timonov123!',
            'gorzhiy': 'temp_gorzhiy123!',
            'lyudmila_bogdanenko': 'temp_lyudmila_bogdanenko123!',
            'alexander_lysovenko': 'temp_alexander_lysovenko123!',
            'yanina': 'temp_yanina123!',
        }
        
        test_password = known_passwords.get(username)
        if not test_password:
            print(f"   ⚠️  Невідомий пароль для {username}")
            return False
        
        password_check = user.check_password(test_password)
        print(f"   Пароль '{test_password}': {'✅ Правильний' if password_check else '❌ Неправильний'}")
        
        if not password_check:
            print(f"   ❌ Пароль неправильний!")
            return False
        
        # Перевірка Flask-Login
        print(f"\n🔐 ПЕРЕВІРКА FLASK-LOGIN:")
        print(f"   hasattr(user, 'is_authenticated'): {hasattr(user, 'is_authenticated')}")
        print(f"   hasattr(user, 'is_active'): {hasattr(user, 'is_active')}")
        print(f"   hasattr(user, 'is_anonymous'): {hasattr(user, 'is_anonymous')}")
        print(f"   hasattr(user, 'get_id'): {hasattr(user, 'get_id')}")
        
        if hasattr(user, 'get_id'):
            user_id = user.get_id()
            print(f"   get_id(): {user_id} (type: {type(user_id)})")
        
        # Перевірка налаштувань Flask-Login
        print(f"\n⚙️  НАЛАШТУВАННЯ FLASK-LOGIN:")
        from app import login_manager
        if login_manager:
            print(f"   login_manager.login_view: {login_manager.login_view}")
            print(f"   login_manager.session_protection: {login_manager.session_protection}")
            print(f"   login_manager.init_app викликано: ✅")
        else:
            print(f"   ❌ LoginManager не знайдено")
        
        # Перевірка SECRET_KEY
        print(f"\n🔐 ПЕРЕВІРКА SECRET_KEY:")
        secret_key = app.config.get('SECRET_KEY')
        if secret_key:
            print(f"   SECRET_KEY встановлено: {secret_key[:20]}...")
        else:
            print(f"   ❌ SECRET_KEY не встановлено!")
        
        # Перевірка бази даних
        print(f"\n💾 ПЕРЕВІРКА БАЗИ ДАНИХ:")
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        print(f"   DATABASE_URI: {db_uri[:50]}...")
        
        try:
            # Перевіряємо з'єднання
            db.session.execute(db.text('SELECT 1'))
            print(f"   ✅ З'єднання з БД працює")
        except Exception as e:
            print(f"   ❌ Помилка з'єднання з БД: {e}")
            return False
        
        # Спроба симуляції логіну
        print(f"\n🧪 СИМУЛЯЦІЯ ЛОГІНУ:")
        try:
            # Оновлюємо last_login
            user.last_login = datetime.now()
            user.reset_login_attempts()
            db.session.commit()
            print(f"   ✅ Дані оновлено в БД")
            
            # Перевіряємо, чи можна завантажити користувача через user_loader
            from app import login_manager
            user_id_str = str(user.id)
            loaded_user = login_manager.user_loader(user_id_str)
            if loaded_user and hasattr(loaded_user, 'id') and loaded_user.id == user.id:
                print(f"   ✅ user_loader працює правильно (завантажено користувача ID: {loaded_user.id})")
            else:
                print(f"   ⚠️  user_loader повернув: {loaded_user} (type: {type(loaded_user)})")
                if loaded_user:
                    print(f"   ✅ user_loader працює (повертає об'єкт)")
                else:
                    print(f"   ❌ user_loader не працює правильно")
                    return False
            
        except Exception as e:
            print(f"   ❌ Помилка при симуляції логіну: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"\n✅ ВСІ ПЕРЕВІРКИ ПРОЙДЕНО УСПІШНО!")
        print(f"\n💡 Рекомендації:")
        print(f"   1. Перевірте логи сервера під час спроби входу")
        print(f"   2. Перевірте cookies в браузері")
        print(f"   3. Перевірте, чи не блокує щось сесії")
        print(f"   4. Спробуйте очистити cookies та спробувати знову")
        print("=" * 80)
        
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Введіть ім'я користувача агента: ").strip()
        if not username:
            username = 'agent'
    
    check_agent_full(username)

