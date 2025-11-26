#!/usr/bin/env python3
"""
Створення агента dnepr_city з паролем та призначенням на anton_admin
"""

import os
import sys
import secrets
import string

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def generate_password(length=12):
    """Генерує безпечний випадковий пароль"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def add_dnepr_city_agent():
    """Створює агента dnepr_city та призначає на anton_admin"""
    
    username = 'dnepr_city'
    
    with app.app_context():
        print("=" * 80)
        print("🔧 СТВОРЕННЯ АГЕНТА dnepr_city")
        print("=" * 80)
        print()
        
        # Перевіряємо, чи вже існує
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"⚠️ {username} вже існує!")
            # Оновлюємо призначення на anton_admin
            anton_admin = User.query.filter_by(username='anton_admin', role='admin').first()
            if anton_admin:
                existing.admin_id = anton_admin.id
                db.session.commit()
                print(f"✅ Призначення оновлено на anton_admin")
            return False
        
        # Знаходимо anton_admin
        anton_admin = User.query.filter_by(username='anton_admin', role='admin').first()
        if not anton_admin:
            print("❌ Адмін anton_admin не знайдено!")
            return False
        
        print(f"✅ Знайдено адміна: anton_admin (ID: {anton_admin.id})")
        print()
        
        # Генеруємо email та пароль
        email = f"{username}@pro-part.online"
        password = generate_password(12)
        
        # Створюємо агента
        new_agent = User(
            username=username,
            email=email,
            role='agent',
            is_active=True,
            is_verified=False,
            admin_id=anton_admin.id  # Призначаємо на anton_admin
        )
        new_agent.set_password(password)
        
        db.session.add(new_agent)
        
        try:
            db.session.commit()
            print("=" * 80)
            print("✅ АГЕНТ СТВОРЕНО УСПІШНО!")
            print("=" * 80)
            print()
            print(f"Логін: {username}")
            print(f"Email: {email}")
            print(f"Пароль: {password}")
            print(f"Призначено на: anton_admin")
            print()
            
            # Зберігаємо пароль у файл
            output_file = 'dnepr_city_password.txt'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("ПАРОЛЬ ДЛЯ АГЕНТА dnepr_city\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Логін: {username}\n")
                f.write(f"Email: {email}\n")
                f.write(f"Пароль: {password}\n")
                f.write(f"Призначено на: anton_admin\n")
                f.write("-" * 80 + "\n")
            
            print(f"📄 Пароль збережено у файл: {output_file}")
            print()
            
            # Показуємо статистику
            anton_total = User.query.filter_by(role='agent', admin_id=anton_admin.id).count()
            print("📊 СТАТИСТИКА:")
            print(f"   anton_admin: {anton_total} агентів")
            print("=" * 80)
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Помилка збереження: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        add_dnepr_city_agent()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

