#!/usr/bin/env python3
"""
Створення відсутніх агентів зі скріншота
"""

import os
import sys
import secrets
import string
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Встановлює новий пароль"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

def generate_password(length=12):
    """Генерує безпечний випадковий пароль"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_missing_agents():
    """Створює відсутніх агентів"""
    # Агенти зі скріншота
    missing_agents = [
        {'username': 'a_ustian'},
        {'username': 'o_antipenko'},
        {'username': 'hatamatapa'},
        {'username': 'yanina_d'},
        {'username': 'o_lisovenko'},
        {'username': 'o_novikov'},
        {'username': 'savoy_finance'},
        {'username': 't_sytnyk'},
    ]
    
    with app.app_context():
        print("=" * 80)
        print("🔧 СТВОРЕННЯ ВІДСУТНІХ АГЕНТІВ")
        print("=" * 80)
        print()
        
        created_count = 0
        skipped_count = 0
        
        passwords = []
        
        for agent_data in missing_agents:
            username = agent_data['username']
            
            # Перевіряємо, чи вже існує
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"⚠️ {username:25} - вже існує, пропускаємо")
                skipped_count += 1
                continue
            
            # Генеруємо email (можна буде змінити пізніше)
            email = f"{username}@pro-part.online"
            
            # Генеруємо пароль
            password = generate_password(12)
            
            # Створюємо агента
            new_agent = User(
                username=username,
                email=email,
                role='agent',
                is_active=True,
                is_verified=False,
                created_at=datetime.utcnow()
            )
            new_agent.set_password(password)
            
            db.session.add(new_agent)
            
            passwords.append({
                'username': username,
                'email': email,
                'password': password
            })
            
            print(f"✅ {username:25} - створено (email: {email}, пароль: {password})")
            created_count += 1
        
        # Зберігаємо всі зміни
        if created_count > 0:
            try:
                db.session.commit()
                print()
                print("=" * 80)
                print(f"✅ СТВОРЕНО: {created_count} агентів")
                print(f"⚠️ ПРОПУЩЕНО: {skipped_count} агентів (вже існують)")
                print("=" * 80)
                print()
                
                # Зберігаємо паролі
                output_file = 'missing_agents_passwords.txt'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write("ПАРОЛІ ДЛЯ СТВОРЕНИХ АГЕНТІВ\n")
                    f.write("=" * 80 + "\n\n")
                    for item in passwords:
                        f.write(f"Логін: {item['username']}\n")
                        f.write(f"Email: {item['email']}\n")
                        f.write(f"Пароль: {item['password']}\n")
                        f.write("-" * 80 + "\n\n")
                
                print(f"📄 Паролі збережено у файл: {output_file}")
                print()
                
                # Виводимо таблицю
                print("=" * 80)
                print("📋 СТВОРЕНІ АГЕНТИ:")
                print("=" * 80)
                print(f"{'Логін':<25} {'Email':<40} {'Пароль':<15}")
                print("-" * 80)
                for item in passwords:
                    print(f"{item['username']:<25} {item['email']:<40} {item['password']:<15}")
                print("=" * 80)
                
                return True
            except Exception as e:
                db.session.rollback()
                print(f"❌ Помилка збереження: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print()
            print("ℹ️ Всі агенти вже існують, нічого не потрібно створювати")
            return False

if __name__ == '__main__':
    try:
        create_missing_agents()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

