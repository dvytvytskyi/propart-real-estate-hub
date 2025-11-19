#!/usr/bin/env python3
"""
Діагностика проблеми з логіном агентів
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def diagnose_login():
    """Діагностує проблеми з логіном"""
    with app.app_context():
        print("=" * 80)
        print("🔍 ДІАГНОСТИКА ПРОБЛЕМИ З ЛОГІНОМ АГЕНТІВ")
        print("=" * 80)
        print()
        
        # 1. Перевірка всіх агентів
        print("1️⃣ Перевірка агентів:")
        agents = User.query.filter_by(role='agent').all()
        
        if not agents:
            print("   ❌ Агентів не знайдено")
            return
        
        print(f"   Знайдено {len(agents)} агентів")
        print()
        
        # 2. Перевірка заблокованих акаунтів
        print("2️⃣ Заблоковані акаунти:")
        locked_count = 0
        for agent in agents:
            if agent.is_account_locked():
                locked_count += 1
                print(f"   🔒 {agent.username} (ID: {agent.id})")
                print(f"      Блокування до: {agent.locked_until}")
                print(f"      Лічильник спроб: {agent.login_attempts}")
        
        if locked_count == 0:
            print("   ✅ Заблокованих акаунтів немає")
        else:
            print(f"   ⚠️ Знайдено {locked_count} заблокованих акаунтів")
        print()
        
        # 3. Перевірка неактивних акаунтів
        print("3️⃣ Неактивні акаунти:")
        inactive_count = 0
        for agent in agents:
            if not agent.is_active:
                inactive_count += 1
                print(f"   ❌ {agent.username} (ID: {agent.id}) - деактивований")
        
        if inactive_count == 0:
            print("   ✅ Всі акаунти активні")
        else:
            print(f"   ⚠️ Знайдено {inactive_count} неактивних акаунтів")
        print()
        
        # 4. Перевірка паролів
        print("4️⃣ Перевірка паролів (тестові паролі):")
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
        
        password_issues = []
        for agent in agents:
            test_password = known_passwords.get(agent.username)
            if test_password:
                password_check = agent.check_password(test_password)
                if not password_check:
                    password_issues.append(agent.username)
                    print(f"   ❌ {agent.username}: пароль '{test_password}' не працює")
        
        if not password_issues:
            print("   ✅ Всі тестові паролі працюють")
        else:
            print(f"   ⚠️ Проблеми з паролями у {len(password_issues)} агентів")
        print()
        
        # 5. Детальна інформація про кожного агента
        print("5️⃣ Детальна інформація про агентів:")
        for agent in agents:
            print(f"   👤 {agent.username} (ID: {agent.id})")
            print(f"      Email: {agent.email}")
            print(f"      Активний: {'✅' if agent.is_active else '❌'}")
            print(f"      Заблокований: {'🔒 Так' if agent.is_account_locked() else '✅ Ні'}")
            print(f"      Лічильник спроб: {agent.login_attempts}")
            if agent.locked_until:
                print(f"      Блокування до: {agent.locked_until}")
            print()
        
        # 6. Рекомендації
        print("=" * 80)
        print("💡 РЕКОМЕНДАЦІЇ:")
        print("=" * 80)
        
        if locked_count > 0:
            print(f"❌ {locked_count} акаунтів заблоковано")
            print("   Виконайте: python3 unlock_user.py <username>")
            print()
        
        if inactive_count > 0:
            print(f"❌ {inactive_count} акаунтів деактивовано")
            print("   Виконайте: python3 << 'EOF'")
            print("   from app import app, db, User")
            print("   with app.app_context():")
            print("       user = User.query.filter_by(username='<username>').first()")
            print("       user.is_active = True")
            print("       db.session.commit()")
            print("EOF")
            print()
        
        if password_issues:
            print(f"❌ Проблеми з паролями у {len(password_issues)} агентів")
            print("   Виконайте: python3 fix_user_login.py <username> <новий_пароль>")
            print()
        
        print("=" * 80)

if __name__ == "__main__":
    diagnose_login()

