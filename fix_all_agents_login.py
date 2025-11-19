#!/usr/bin/env python3
"""
Швидке виправлення всіх проблем з логіном агентів
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def fix_all_agents():
    """Виправляє всі проблеми з логіном агентів"""
    with app.app_context():
        print("=" * 80)
        print("🔧 ВИПРАВЛЕННЯ ПРОБЛЕМ З ЛОГІНОМ АГЕНТІВ")
        print("=" * 80)
        print()
        
        agents = User.query.filter_by(role='agent').all()
        
        if not agents:
            print("❌ Агентів не знайдено")
            return
        
        print(f"📋 Знайдено {len(agents)} агентів")
        print()
        
        fixed_count = 0
        
        for agent in agents:
            fixed = False
            
            # 1. Розблоковуємо акаунт
            if agent.is_account_locked():
                agent.unlock_account()
                fixed = True
                print(f"   🔓 Розблоковано: {agent.username}")
            
            # 2. Активуємо акаунт
            if not agent.is_active:
                agent.is_active = True
                fixed = True
                print(f"   ✅ Активовано: {agent.username}")
            
            # 3. Скидаємо лічильник спроб
            if agent.login_attempts > 0:
                agent.reset_login_attempts()
                fixed = True
                print(f"   🔄 Скинуто спроби: {agent.username} (було {agent.login_attempts})")
            
            if fixed:
                fixed_count += 1
        
        if fixed_count > 0:
            db.session.commit()
            print()
            print(f"✅ Виправлено {fixed_count} агентів")
        else:
            print("✅ Всі агенти вже налаштовані правильно")
        
        print()
        print("=" * 80)
        print("💡 ТЕСТОВІ ПАРОЛІ:")
        print("=" * 80)
        
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
        
        for agent in agents:
            test_password = known_passwords.get(agent.username)
            if test_password:
                password_check = agent.check_password(test_password)
                status = "✅" if password_check else "❌"
                print(f"   {status} {agent.username}: {test_password}")
        
        print()
        print("=" * 80)

if __name__ == "__main__":
    fix_all_agents()

