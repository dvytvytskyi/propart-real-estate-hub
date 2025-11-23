#!/usr/bin/env python3
"""
Діагностика проблем з логіном агентів
Перевіряє стан акаунтів агентів та можливі проблеми
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

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
    is_verified = db.Column(db.Boolean, default=False)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    
    def is_account_locked(self):
        if self.locked_until:
            return datetime.now() < self.locked_until
        return False
    
    def check_password(self, password):
        if self.password_hash.startswith('pbkdf2:sha256'):
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)
        return bcrypt.check_password_hash(self.password_hash, password)

def diagnose_agent_login(username, test_password=None):
    """Діагностика проблем з логіном для конкретного агента"""
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Користувач '{username}' не знайдено!")
            return
        
        print("=" * 80)
        print(f"🔍 ДІАГНОСТИКА ЛОГІНУ ДЛЯ: {username}")
        print("=" * 80)
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Роль: {user.role}")
        print()
        
        # Перевірка 1: is_active
        print("1️⃣ Перевірка is_active:")
        if user.is_active:
            print("   ✅ Акаунт активний")
        else:
            print("   ❌ АКАУНТ ДЕАКТИВОВАНИЙ - це блокує логін!")
            print("   🔧 Виправлення: встановіть user.is_active = True")
        print()
        
        # Перевірка 2: Блокування
        print("2️⃣ Перевірка блокування акаунту:")
        if user.is_account_locked():
            print(f"   ❌ АКАУНТ ЗАБЛОКОВАНИЙ до {user.locked_until}")
            print(f"   🔧 Виправлення: встановіть user.locked_until = None")
        else:
            print("   ✅ Акаунт не заблокований")
        print()
        
        # Перевірка 3: Логіни
        print("3️⃣ Перевірка спроб входу:")
        print(f"   Невдалих спроб: {user.login_attempts}")
        if user.login_attempts >= 5:
            print("   ⚠️ Багато невдалих спроб (>= 5)")
        print()
        
        # Перевірка 4: Пароль
        print("4️⃣ Перевірка паролю:")
        if user.password_hash:
            hash_type = "bcrypt" if not user.password_hash.startswith('pbkdf2') else "werkzeug"
            print(f"   Тип хешу: {hash_type}")
            print(f"   Хеш (перші 30 символів): {user.password_hash[:30]}...")
            
            if test_password:
                if user.check_password(test_password):
                    print(f"   ✅ Пароль '{test_password}' ПРАВИЛЬНИЙ")
                else:
                    print(f"   ❌ Пароль '{test_password}' НЕПРАВИЛЬНИЙ")
            else:
                print("   ⚠️ Пароль не перевірявся (не надано test_password)")
        else:
            print("   ❌ Пароль не встановлено!")
        print()
        
        # Перевірка 5: Верифікація (не повинна блокувати логін, але покажемо)
        print("5️⃣ Статус верифікації:")
        if user.is_verified:
            print("   ✅ Агент верифікований")
        else:
            print("   ⚠️ Агент не верифікований (не повинно блокувати логін)")
        print()
        
        # Підсумок
        print("=" * 80)
        print("📋 ПІДСУМОК:")
        print("=" * 80)
        issues = []
        if not user.is_active:
            issues.append("❌ Акаунт деактивований (is_active = False)")
        if user.is_account_locked():
            issues.append(f"❌ Акаунт заблокований до {user.locked_until}")
        if user.login_attempts >= 5:
            issues.append(f"⚠️ Багато невдалих спроб ({user.login_attempts})")
        
        if issues:
            print("Знайдені проблеми:")
            for issue in issues:
                print(f"  {issue}")
            print()
            print("🔧 КОМАНДИ ДЛЯ ВИПРАВЛЕННЯ:")
            print(f"   python fix_agent_login.py {username}")
        else:
            print("✅ Жодних очевидних проблем не знайдено")
            print("   Можливо, проблема в перевірці паролю або CSRF токені")
        print()

def diagnose_all_agents():
    """Діагностика всіх агентів"""
    with app.app_context():
        agents = User.query.filter_by(role='agent').all()
        
        print("=" * 80)
        print("🔍 ДІАГНОСТИКА ВСІХ АГЕНТІВ")
        print("=" * 80)
        print()
        
        inactive_count = 0
        locked_count = 0
        
        for agent in agents:
            issues = []
            if not agent.is_active:
                issues.append("❌ Деактивований")
                inactive_count += 1
            if agent.is_account_locked():
                issues.append(f"🔒 Заблокований до {agent.locked_until}")
                locked_count += 1
            if agent.login_attempts >= 5:
                issues.append(f"⚠️ Багато спроб ({agent.login_attempts})")
            
            status = ", ".join(issues) if issues else "✅ OK"
            print(f"  {agent.username:20} | {status}")
        
        print()
        print("=" * 80)
        print(f"📊 ПІДСУМОК:")
        print(f"  Всього агентів: {len(agents)}")
        print(f"  Деактивованих: {inactive_count}")
        print(f"  Заблокованих: {locked_count}")
        print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        username = sys.argv[1]
        test_password = sys.argv[2] if len(sys.argv) > 2 else None
        diagnose_agent_login(username, test_password)
    else:
        diagnose_all_agents()

