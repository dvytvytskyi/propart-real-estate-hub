#!/usr/bin/env python3
"""
Створює нові паролі для всіх агентів
Генерує безпечні випадкові паролі та зберігає їх у файл
"""

import os
import sys
import secrets
import string
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
    
    def set_password(self, password):
        """Встановлює новий пароль"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

def generate_password(length=12):
    """Генерує безпечний випадковий пароль"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def reset_all_agents_passwords():
    """Створює нові паролі для всіх агентів"""
    with app.app_context():
        # Отримуємо всіх агентів
        agents = User.query.filter_by(role='agent').order_by(User.username).all()
        
        if not agents:
            print("❌ Агентів не знайдено!")
            return
        
        passwords = []
        
        print("=" * 80)
        print("🔐 СТВОРЕННЯ НОВИХ ПАРОЛІВ ДЛЯ ВСІХ АГЕНТІВ")
        print("=" * 80)
        print()
        
        for agent in agents:
            new_password = generate_password(12)
            
            # Встановлюємо новий пароль
            agent.set_password(new_password)
            
            passwords.append({
                'id': agent.id,
                'username': agent.username,
                'email': agent.email,
                'password': new_password
            })
            
            print(f"✅ {agent.username:20} | Email: {agent.email:30} | Пароль: {new_password}")
        
        # Зберігаємо всі зміни
        try:
            db.session.commit()
            print()
            print("=" * 80)
            print("✅ ВСІ ПАРОЛІ УСПІШНО ОНОВЛЕНО!")
            print("=" * 80)
            print()
            
            # Зберігаємо в файл для безпеки
            output_file = 'agents_passwords.txt'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("СПИСОК ЛОГІНІВ ТА ПАРОЛІВ ДЛЯ АГЕНТІВ\n")
                f.write("=" * 80 + "\n")
                f.write(f"Дата створення: {os.popen('date').read().strip()}\n")
                f.write("=" * 80 + "\n\n")
                
                for item in passwords:
                    f.write(f"ID: {item['id']}\n")
                    f.write(f"Логін: {item['username']}\n")
                    f.write(f"Email: {item['email']}\n")
                    f.write(f"Пароль: {item['password']}\n")
                    f.write("-" * 80 + "\n\n")
            
            print(f"📄 Список збережено у файл: {output_file}")
            print()
            
            # Виводимо таблицю
            print("=" * 80)
            print("📋 СПИСОК АГЕНТІВ З НОВИМИ ПАРОЛЯМИ:")
            print("=" * 80)
            print(f"{'№':<4} {'Логін':<20} {'Email':<35} {'Пароль':<15}")
            print("-" * 80)
            
            for idx, item in enumerate(passwords, 1):
                print(f"{idx:<4} {item['username']:<20} {item['email']:<35} {item['password']:<15}")
            
            print("=" * 80)
            print()
            print("⚠️  ВАЖЛИВО: Збережіть ці дані у безпечному місці!")
            print("   Паролі збережено у файл:", output_file)
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Помилка збереження: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

if __name__ == '__main__':
    try:
        reset_all_agents_passwords()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

