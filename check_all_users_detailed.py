#!/usr/bin/env python3
"""
Детальна перевірка всіх користувачів в системі
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/real_estate_agents.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)

def check_all_users():
    """Показує всіх користувачів в системі"""
    with app.app_context():
        # Отримуємо ВСІХ користувачів (включно з неактивними)
        all_users = User.query.order_by(User.role, User.username).all()
        
        # Агенти зі скріншота
        screen_agents = ['a_ustian', 'o_antipenko', 'hatamatapa', 'yanina_d', 
                        'o_lisovenko', 'o_novikov', 'savoy_finance', 't_sytnyk']
        
        print("=" * 80)
        print("📋 ВСІ КОРИСТУВАЧІ В СИСТЕМІ (включно з неактивними)")
        print("=" * 80)
        print()
        
        print(f"{'ID':<5} {'Логін':<25} {'Email':<40} {'Роль':<10} {'Активний':<10} {'Створено':<20}")
        print("-" * 80)
        
        found_agents = []
        missing_agents = []
        
        for user in all_users:
            active = '✅ Так' if user.is_active else '❌ Ні'
            created = user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A'
            print(f"{user.id:<5} {user.username:<25} {user.email:<40} {user.role:<10} {active:<10} {created:<20}")
            
            if user.username in screen_agents:
                found_agents.append(user.username)
        
        print()
        print("=" * 80)
        print(f"📊 ВСЬОГО КОРИСТУВАЧІВ: {len(all_users)}")
        print("=" * 80)
        print()
        
        # Перевірка агентів зі скріншота
        print("🔍 ПЕРЕВІРКА АГЕНТІВ ЗІ СКРІНШОТА:")
        print("-" * 80)
        for agent_name in screen_agents:
            user = User.query.filter_by(username=agent_name).first()
            if user:
                status = "✅ Знайдено" + (" (неактивний)" if not user.is_active else "")
                print(f"  {agent_name:<25} {status}")
            else:
                print(f"  {agent_name:<25} ❌ НЕ ЗНАЙДЕНО")
                missing_agents.append(agent_name)
        
        print()
        if missing_agents:
            print("⚠️ АГЕНТИ, ЯКІ НЕ ЗНАЙДЕНІ В СИСТЕМІ:")
            for agent in missing_agents:
                print(f"  - {agent}")
        else:
            print("✅ Всі агенти зі скріншота знайдені!")
        print()

if __name__ == '__main__':
    try:
        check_all_users()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

