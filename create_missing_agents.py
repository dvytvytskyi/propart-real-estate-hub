#!/usr/bin/env python3
"""
Скрипт для створення відсутніх агентів, знайдених в HubSpot
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

def create_missing_agents():
    """Створює відсутніх агентів на основі даних з HubSpot"""
    with app.app_context():
        print("=" * 80)
        print("👥 СТВОРЕННЯ ВІДСУТНІХ АГЕНТІВ")
        print("=" * 80)
        
        # Список агентів, знайдених в HubSpot
        # Використовуємо найбільш поширені варіанти імен
        agents_to_create = [
            {
                'username': 'olena_birovchak',
                'display_name': 'Олена Біровчак',
                'email': 'olena.birovchak@propart.com',
                'role': 'agent'
            },
            {
                'username': 'ustyan',
                'display_name': 'Устьян',
                'email': 'ustyan@propart.com',
                'role': 'agent'
            },
            {
                'username': 'alexander_novikov',
                'display_name': 'Александр Новиков',
                'email': 'alexander.novikov@propart.com',
                'role': 'agent'
            },
            {
                'username': 'uik',
                'display_name': 'UIK',
                'email': 'uik@propart.com',
                'role': 'agent'
            },
            {
                'username': 'blagovest',
                'display_name': 'Благовест',
                'email': 'blagovest@propart.com',
                'role': 'agent'
            },
            {
                'username': 'timonov',
                'display_name': 'Timonov',
                'email': 'timonov@propart.com',
                'role': 'agent'
            },
            {
                'username': 'gorzhiy',
                'display_name': 'Gorzhiy',
                'email': 'gorzhiy@propart.com',
                'role': 'agent'
            },
            {
                'username': 'lyudmila_bogdanenko',
                'display_name': 'Людмила Богданенко',
                'email': 'lyudmila.bogdanenko@propart.com',
                'role': 'agent'
            },
            {
                'username': 'alexander_lysovenko',
                'display_name': 'Александр Лисовенко',
                'email': 'alexander.lysovenko@propart.com',
                'role': 'agent'
            },
            {
                'username': 'yanina',
                'display_name': 'Янина',
                'email': 'yanina@propart.com',
                'role': 'agent'
            },
        ]
        
        # Також додаємо варіанти імен для маппінгу
        name_mapping = {
            'Олена Біровчак': 'olena_birovchak',
            'Бировчак Лена': 'olena_birovchak',
            'Біровчак Олена': 'olena_birovchak',
            'Олена Бировчак': 'olena_birovchak',
            'Бировчак Олена': 'olena_birovchak',
            'Устьян': 'ustyan',
            'Новиков Александр': 'alexander_novikov',
            'Александр Новиков': 'alexander_novikov',
            'UIK': 'uik',
            'Благовест': 'blagovest',
            'Timonov': 'timonov',
            'Gorzhiy': 'gorzhiy',
            'Людмила Богданенко': 'lyudmila_bogdanenko',
            'Александр Лисовенко': 'alexander_lysovenko',
            'Янина': 'yanina',
        }
        
        created_count = 0
        skipped_count = 0
        
        print("\n📋 Перевірка та створення агентів...")
        print("-" * 80)
        
        for agent_data in agents_to_create:
            # Перевіряємо, чи існує користувач з таким username або email
            existing_user = User.query.filter(
                (User.username == agent_data['username']) |
                (User.email == agent_data['email'])
            ).first()
            
            if existing_user:
                print(f"   ⏭️  {agent_data['display_name']} ({agent_data['username']}) - вже існує")
                skipped_count += 1
                continue
            
            # Створюємо нового користувача
            new_user = User(
                username=agent_data['username'],
                email=agent_data['email'],
                role=agent_data['role'],
                is_active=True,
                is_verified=True
            )
            
            # Генеруємо тимчасовий пароль (можна буде змінити пізніше)
            temp_password = f"temp_{agent_data['username']}123!"
            new_user.set_password(temp_password)
            
            db.session.add(new_user)
            created_count += 1
            
            print(f"   ✅ Створено: {agent_data['display_name']}")
            print(f"      Username: {agent_data['username']}")
            print(f"      Email: {agent_data['email']}")
            print(f"      Password: {temp_password}")
            print()
        
        db.session.commit()
        
        print("=" * 80)
        print("📊 РЕЗУЛЬТАТИ:")
        print(f"   Створено: {created_count}")
        print(f"   Пропущено (вже існують): {skipped_count}")
        print("=" * 80)
        
        # Виводимо маппінг для використання
        print("\n📋 МАППІНГ ІМЕН ДЛЯ HUBSPOT:")
        print("-" * 80)
        for hubspot_name, username in sorted(name_mapping.items()):
            user = User.query.filter_by(username=username).first()
            if user:
                print(f"   '{hubspot_name}' → {username} (ID: {user.id})")
        
        print("\n💡 Тепер можна запустити fix_agent_assignment.py --apply для призначення агентів")
        print("=" * 80)

if __name__ == "__main__":
    create_missing_agents()

