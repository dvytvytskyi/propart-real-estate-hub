#!/usr/bin/env python3
"""
Скрипт налаштування Real Estate Agents Hub
"""

from app import app, db, User
from werkzeug.security import generate_password_hash
import os

def setup_database():
    """Створення бази даних та тестових користувачів"""
    with app.app_context():
        # Створюємо таблиці
        db.create_all()
        print("✅ База даних створена")
        
        # Створюємо адміна
        existing_admin = User.query.filter_by(username='admin').first()
        if not existing_admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            print("✅ Адмін створено: admin / admin123")
        else:
            print("ℹ️  Адмін вже існує")
        
        # Створюємо агента
        existing_agent = User.query.filter_by(username='agent').first()
        if not existing_agent:
            agent = User(
                username='agent',
                email='agent@example.com',
                password_hash=generate_password_hash('agent123'),
                role='agent'
            )
            db.session.add(agent)
            print("✅ Агент створено: agent / agent123")
        else:
            print("ℹ️  Агент вже існує")
        
        db.session.commit()
        
        print("\n📋 Всі користувачі в системі:")
        users = User.query.all()
        for user in users:
            print(f"   - {user.username} ({user.role}) - {user.email}")

def check_environment():
    """Перевірка налаштувань середовища"""
    print("🔧 Перевірка налаштувань...")
    
    # Перевіряємо .env файл
    if not os.path.exists('.env'):
        print("⚠️  Файл .env не знайдено")
        print("   Скопіюйте env_example.txt в .env та налаштуйте HubSpot API ключ")
        return False
    
    # Перевіряємо HubSpot API ключ
    from dotenv import load_dotenv
    load_dotenv()
    
    hubspot_key = os.getenv('HUBSPOT_API_KEY')
    if not hubspot_key or hubspot_key == 'your-hubspot-api-key-here':
        print("⚠️  HubSpot API ключ не налаштований")
        print("   Додайте ваш API ключ в .env файл")
        return False
    
    print("✅ Налаштування середовища OK")
    return True

if __name__ == '__main__':
    print("🏠 Налаштування Real Estate Agents Hub")
    print("=" * 50)
    
    # Налаштовуємо базу даних
    setup_database()
    
    print("\n" + "=" * 50)
    
    # Перевіряємо налаштування
    env_ok = check_environment()
    
    print("\n" + "=" * 50)
    print("🚀 Готово! Запустіть додаток командою:")
    print("   python run.py")
    print("\n🌐 Потім відкрийте браузер: http://localhost:5000")
    
    if not env_ok:
        print("\n⚠️  Не забудьте налаштувати HubSpot API!")
        print("   Дивіться інструкції в HUBSPOT_SETUP.md")
