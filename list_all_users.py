#!/usr/bin/env python3
"""
Скрипт для виведення списку всіх користувачів у системі
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def list_all_users():
    """Виводить список всіх користувачів"""
    with app.app_context():
        print("=" * 80)
        print("👥 СПИСОК ВСІХ КОРИСТУВАЧІВ У СИСТЕМІ")
        print("=" * 80)
        
        users = User.query.order_by(User.id).all()
        
        if not users:
            print("❌ Користувачів не знайдено")
            return
        
        print(f"\n📋 Всього користувачів: {len(users)}\n")
        print("-" * 80)
        print(f"{'ID':<5} {'Username':<25} {'Email':<35} {'Роль':<12} {'Статус':<10} {'Пароль'}")
        print("-" * 80)
        
        # Відомі паролі з документації
        known_passwords = {
            'admin': 'admin123',
            'anton_admin': 'sfajerfe234ewqf#',
            'alex_admin': 'dgerifwef@fmso4',
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
        
        for user in users:
            status = "✅ Активний" if user.is_active else "❌ Неактивний"
            password = known_passwords.get(user.username, 'Невідомий')
            
            print(f"{user.id:<5} {user.username:<25} {user.email:<35} {user.role:<12} {status:<10} {password}")
        
        print("-" * 80)
        
        # Групування по ролях
        print("\n📊 СТАТИСТИКА ПО РОЛЯХ:")
        print("-" * 80)
        roles = {}
        for user in users:
            if user.role not in roles:
                roles[user.role] = []
            roles[user.role].append(user)
        
        for role, role_users in sorted(roles.items()):
            print(f"\n{role.upper()} ({len(role_users)}):")
            for user in role_users:
                password = known_passwords.get(user.username, 'Невідомий')
                print(f"   • {user.username:<25} | {user.email:<35} | Пароль: {password}")
        
        print("\n" + "=" * 80)
        print("💡 Для зміни пароля використовуйте:")
        print("   python fix_user_login.py <username> <новий_пароль>")
        print("=" * 80)

if __name__ == "__main__":
    list_all_users()

