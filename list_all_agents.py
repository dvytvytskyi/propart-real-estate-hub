#!/usr/bin/env python3
"""
Скрипт для виводу списку всіх агентів та їх даних
Паролі не можна відновити, але можна встановити нові
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# Додаємо батьківську директорію в шлях
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Створюємо Flask додаток
app = Flask(__name__)

# Завантажуємо конфігурацію
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/real_estate_agents.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Модель User (спрощена версія)
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    commission = db.Column(db.Float, default=0.0)
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.String(20), default='bronze')
    total_leads = db.Column(db.Integer, default=0)
    closed_deals = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False)
    verification_requested = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    admin = db.relationship('User', remote_side=[id], backref='brokers')

def get_all_agents():
    """Отримує список всіх агентів"""
    with app.app_context():
        # Отримуємо всіх користувачів
        users = User.query.order_by(User.role, User.username).all()
        
        print("=" * 80)
        print("📋 СПИСОК ВСІХ КОРИСТУВАЧІВ")
        print("=" * 80)
        print()
        
        # Адміністратори
        admins = [u for u in users if u.role == 'admin']
        if admins:
            print("👑 АДМІНІСТРАТОРИ:")
            print("-" * 80)
            for admin in admins:
                print(f"  ID: {admin.id}")
                print(f"  Логін: {admin.username}")
                print(f"  Email: {admin.email}")
                print(f"  Створено: {admin.created_at.strftime('%Y-%m-%d %H:%M:%S') if admin.created_at else 'N/A'}")
                print(f"  Останній вхід: {admin.last_login.strftime('%Y-%m-%d %H:%M:%S') if admin.last_login else 'Ніколи'}")
                print(f"  Активний: {'✅ Так' if admin.is_active else '❌ Ні'}")
                print(f"  Пароль: [ХЕШОВАНИЙ - НЕ МОЖНА ВІДНОВИТИ]")
                print()
        
        # Агенти
        agents = [u for u in users if u.role == 'agent']
        if agents:
            print("👤 АГЕНТИ:")
            print("-" * 80)
            for agent in agents:
                admin_name = agent.admin.username if agent.admin else "Не призначено"
                print(f"  ID: {agent.id}")
                print(f"  Логін: {agent.username}")
                print(f"  Email: {agent.email}")
                print(f"  Адмін: {admin_name}")
                print(f"  Верифікований: {'✅ Так' if agent.is_verified else '❌ Ні'}")
                print(f"  Активний: {'✅ Так' if agent.is_active else '❌ Ні'}")
                print(f"  Створено: {agent.created_at.strftime('%Y-%m-%d %H:%M:%S') if agent.created_at else 'N/A'}")
                print(f"  Останній вхід: {agent.last_login.strftime('%Y-%m-%d %H:%M:%S') if agent.last_login else 'Ніколи'}")
                print(f"  Комісія: {agent.commission}%")
                print(f"  Поінти: {agent.points} (Рівень: {agent.level})")
                print(f"  Лідів: {agent.total_leads} | Угод: {agent.closed_deals}")
                print(f"  Пароль: [ХЕШОВАНИЙ - НЕ МОЖНА ВІДНОВИТИ]")
                print()
        
        print("=" * 80)
        print(f"📊 ПІДСУМОК:")
        print(f"  Всього користувачів: {len(users)}")
        print(f"  Адміністраторів: {len(admins)}")
        print(f"  Агентів: {len(agents)}")
        print("=" * 80)
        print()
        print("⚠️  УВАГА: Паролі зберігаються в хешованому вигляді і не можуть бути відновлені.")
        print("   Для встановлення нового паролю використовуйте скрипт reset_agent_password.py")
        print()

if __name__ == '__main__':
    try:
        get_all_agents()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

