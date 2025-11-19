#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки логіну агентів
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def test_agent_login():
    """Тестує логін агентів"""
    with app.app_context():
        print("=" * 80)
        print("🔍 ТЕСТУВАННЯ ЛОГІНУ АГЕНТІВ")
        print("=" * 80)
        
        agents = User.query.filter_by(role='agent').all()
        
        if not agents:
            print("❌ Агентів не знайдено")
            return
        
        print(f"\n📋 Знайдено {len(agents)} агентів\n")
        
        for agent in agents:
            print(f"👤 {agent.username} (ID: {agent.id})")
            print(f"   Email: {agent.email}")
            print(f"   Активний: {'✅' if agent.is_active else '❌'}")
            print(f"   Заблокований: {'🔒 Так' if agent.is_account_locked() else '✅ Ні'}")
            print(f"   Лічильник спроб: {agent.login_attempts}")
            print(f"   Блокування до: {agent.locked_until.strftime('%Y-%m-%d %H:%M:%S') if agent.locked_until else 'Немає'}")
            
            # Перевіряємо пароль
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
            
            test_password = known_passwords.get(agent.username, 'НЕВІДОМИЙ')
            
            if test_password != 'НЕВІДОМИЙ':
                password_check = agent.check_password(test_password)
                print(f"   Пароль '{test_password}': {'✅ Правильний' if password_check else '❌ Неправильний'}")
            else:
                print(f"   Пароль: {test_password}")
            
            print()
        
        print("=" * 80)
        print("💡 Якщо пароль неправильний, використовуйте:")
        print("   python fix_user_login.py <username> <новий_пароль>")
        print("=" * 80)

if __name__ == "__main__":
    test_agent_login()

