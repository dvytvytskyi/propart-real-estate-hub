#!/usr/bin/env python3
"""
Скрипт для скидання/встановлення нового паролю для агента
Використання: python reset_agent_password.py <username> <new_password>
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
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

# Модель User
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')
    
    def set_password(self, password):
        """Встановлює новий пароль"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

def reset_password(username, new_password):
    """Скидає пароль для користувача"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувач з логіном '{username}' не знайдено!")
            return False
        
        old_hash = user.password_hash[:20] + "..."
        user.set_password(new_password)
        db.session.commit()
        
        print("=" * 80)
        print("✅ ПАРОЛЬ УСПІШНО ОНОВЛЕНО")
        print("=" * 80)
        print(f"  Користувач: {user.username} ({user.role})")
        print(f"  Email: {user.email}")
        print(f"  Старий хеш: {old_hash}")
        print(f"  Новий пароль: {new_password}")
        print("=" * 80)
        return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Використання: python reset_agent_password.py <username> <new_password>")
        print()
        print("Приклад:")
        print("  python reset_agent_password.py agent1 newpassword123")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    if len(new_password) < 6:
        print("❌ Пароль повинен містити мінімум 6 символів!")
        sys.exit(1)
    
    try:
        reset_password(username, new_password)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

