#!/usr/bin/env python3
"""
Скрипт для перевірки заблокованих користувачів
"""

import sys
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def check_locked_users():
    """Перевіряє всіх користувачів на блокування"""
    with app.app_context():
        users = User.query.all()
        
        print("🔍 Перевірка користувачів на блокування")
        print("=" * 80)
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Спроби':<8} {'Заблоковано до':<20} {'Статус'}")
        print("-" * 80)
        
        locked_found = False
        for user in users:
            attempts = user.login_attempts or 0
            locked_until_str = "Немає"
            status = "✅ Активний"
            
            if user.locked_until:
                if user.is_account_locked():
                    locked_until_str = user.locked_until.strftime("%Y-%m-%d %H:%M:%S")
                    status = "🔒 ЗАБЛОКОВАНО"
                    locked_found = True
                else:
                    locked_until_str = f"{user.locked_until.strftime('%Y-%m-%d %H:%M:%S')} (минуло)"
                    status = "⏰ Було заблоковано"
            
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {attempts:<8} {locked_until_str:<20} {status}")
        
        print("-" * 80)
        if not locked_found:
            print("✅ Заблокованих користувачів не знайдено")
        else:
            print("⚠️  Знайдено заблокованих користувачів")

if __name__ == "__main__":
    check_locked_users()

