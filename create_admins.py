#!/usr/bin/env python3
"""
Створення адмінів для системи
Виконується один раз перед деплоєм
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admins():
    """Створює адмінів якщо їх немає"""
    with app.app_context():
        try:
            print("=" * 60)
            print("👥 СТВОРЕННЯ АДМІНІВ")
            print("=" * 60)
            
            # Перевірити чи існують адміни
            existing_admins = User.query.filter_by(role='admin').all()
            
            if existing_admins:
                print(f"\n✅ Знайдено {len(existing_admins)} адмінів:")
                for admin in existing_admins:
                    print(f"   - {admin.username} ({admin.email})")
                print("\n❓ Створити додаткових адмінів? (y/N): ", end='')
                response = input().lower()
                if response != 'y':
                    print("❌ Скасовано")
                    return
            
            # Адміни для створення
            admins_to_create = [
                {
                    'username': 'anton_admin',
                    'email': 'anton@pro-part.online',
                    'password': 'sfajerfe234ewqf#'
                },
                {
                    'username': 'alex_admin',
                    'email': 'alex@pro-part.online',
                    'password': 'dgerifwef@fmso4'
                }
            ]
            
            print("\n📝 Створюю адмінів...")
            created = 0
            
            for admin_data in admins_to_create:
                # Перевірка чи вже існує
                existing = User.query.filter(
                    (User.username == admin_data['username']) | 
                    (User.email == admin_data['email'])
                ).first()
                
                if existing:
                    print(f"   ⚠️  {admin_data['username']} вже існує (пропущено)")
                    continue
                
                # Створення адміна
                admin = User(
                    username=admin_data['username'],
                    email=admin_data['email'],
                    password_hash=generate_password_hash(admin_data['password']),
                    role='admin',
                    is_verified=True
                )
                
                db.session.add(admin)
                print(f"   ✅ {admin_data['username']} створено")
                created += 1
            
            db.session.commit()
            
            print("\n" + "=" * 60)
            print(f"✅ Створено {created} нових адмінів")
            print("=" * 60)
            
            # Показати всіх адмінів
            all_admins = User.query.filter_by(role='admin').all()
            print(f"\n📋 ВСІ АДМІНИ В СИСТЕМІ ({len(all_admins)}):")
            for admin in all_admins:
                print(f"   👤 {admin.username:20} | {admin.email:35} | ID: {admin.id}")
            
            print("\n" + "=" * 60)
            print("🔐 ОБЛІКОВІ ЗАПИСИ:")
            print("=" * 60)
            print("1. anton_admin / sfajerfe234ewqf#")
            print("2. alex_admin / dgerifwef@fmso4")
            print("=" * 60)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Помилка: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    create_admins()

