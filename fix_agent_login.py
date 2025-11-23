#!/usr/bin/env python3
"""
Виправлення проблем з логіном агентів
Розблокує акаунт та активує його
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/real_estate_agents.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')
    is_active = db.Column(db.Boolean, default=True)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)

def fix_agent_login(username):
    """Виправляє проблеми з логіном для агента"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувач '{username}' не знайдено!")
            return False
        
        print("=" * 80)
        print(f"🔧 ВИПРАВЛЕННЯ ЛОГІНУ ДЛЯ: {username}")
        print("=" * 80)
        
        fixed = False
        
        # Виправлення 1: Активація акаунту
        if not user.is_active:
            print("🔧 Активація акаунту...")
            user.is_active = True
            fixed = True
        
        # Виправлення 2: Розблокування акаунту
        if user.locked_until:
            print("🔧 Розблокування акаунту...")
            user.locked_until = None
            fixed = True
        
        # Виправлення 3: Скидання спроб входу
        if user.login_attempts > 0:
            print(f"🔧 Скидання спроб входу (було {user.login_attempts})...")
            user.login_attempts = 0
            fixed = True
        
        if fixed:
            db.session.commit()
            print()
            print("✅ ПРОБЛЕМИ ВИПРАВЛЕНО!")
            print(f"   Користувач: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Активний: {'✅ Так' if user.is_active else '❌ Ні'}")
            print(f"   Заблокований: {'❌ Так' if user.locked_until else '✅ Ні'}")
            print(f"   Спроби входу: {user.login_attempts}")
            print("=" * 80)
            return True
        else:
            print("ℹ️ Жодних проблем не знайдено для виправлення")
            print("=" * 80)
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Використання: python fix_agent_login.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    
    try:
        fix_agent_login(username)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

