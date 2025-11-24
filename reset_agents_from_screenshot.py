#!/usr/bin/env python3
"""
Видалення всіх агентів (окрім olena_birovchak та адмінів) та додавання нових зі скріншота
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

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class UserDocument(db.Model):
    __tablename__ = 'user_document'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

def generate_password(length=12):
    """Генерує безпечний випадковий пароль"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def reset_agents():
    """Видаляє всіх агентів (окрім olena та адмінів) та додає нових"""
    # Агенти зі скріншота (вже є адміни: admin, alex_admin, anton_admin)
    agents_from_screenshot = [
        {'username': 'a_ustian', 'role': 'agent'},
        {'username': 'o_lisovenko', 'role': 'agent'},
        {'username': 'o_novikov', 'role': 'agent'},
        {'username': 'savoy_finance', 'role': 'agent'},
        {'username': 't_sytnyk', 'role': 'agent'},
        # olena_birovchak залишаємо, не додаємо до списку
    ]
    
    with app.app_context():
        print("=" * 80)
        print("🔄 СКИДАННЯ ТА ДОДАВАННЯ АГЕНТІВ")
        print("=" * 80)
        print()
        
        # 1. Отримуємо всіх користувачів
        all_users = User.query.all()
        
        # 2. Знаходимо користувачів для видалення (всі агенти, окрім olena_birovchak)
        users_to_delete = []
        users_to_keep = []
        
        for user in all_users:
            if user.role == 'agent' and user.username != 'olena_birovchak':
                users_to_delete.append(user)
            else:
                users_to_keep.append(user)
        
        print(f"📋 Знайдено користувачів для видалення: {len(users_to_delete)}")
        print(f"📋 Залишається користувачів: {len(users_to_keep)}")
        print()
        
        # 3. Перевіряємо, чи є ліди у користувачів, яких видаляємо
        leads_to_reassign = []
        for user in users_to_delete:
            leads_count = Lead.query.filter_by(agent_id=user.id).count()
            if leads_count > 0:
                leads_to_reassign.append({
                    'user': user,
                    'leads_count': leads_count
                })
                print(f"⚠️ У користувача {user.username} є {leads_count} лідів")
        
        if leads_to_reassign:
            print()
            print("⚠️ УВАГА: У видаляємих користувачів є ліди!")
            print("   Ліди будуть перепризначені на olena_birovchak")
            print()
        
        # 4. Перепризначуємо ліди на olena_birovchak
        olena = User.query.filter_by(username='olena_birovchak').first()
        if olena:
            for item in leads_to_reassign:
                Lead.query.filter_by(agent_id=item['user'].id).update({'agent_id': olena.id})
                print(f"✅ {item['leads_count']} лідів перепризначено з {item['user'].username} на olena_birovchak")
        
        # 5. Спочатку видаляємо документи користувачів (щоб уникнути ForeignKey constraint)
        deleted_docs_count = 0
        for user in users_to_delete:
            docs = UserDocument.query.filter_by(user_id=user.id).all()
            for doc in docs:
                db.session.delete(doc)
                deleted_docs_count += 1
        
        if deleted_docs_count > 0:
            print(f"🗑️ Видаляємо {deleted_docs_count} документів користувачів...")
            db.session.commit()
        
        # 6. Тепер видаляємо користувачів
        deleted_count = 0
        for user in users_to_delete:
            print(f"🗑️ Видаляємо: {user.username} ({user.email})")
            db.session.delete(user)
            deleted_count += 1
        
        if deleted_count > 0:
            db.session.commit()
            print()
            print(f"✅ Видалено: {deleted_count} користувачів")
            print()
        
        # 7. Додаємо нових агентів
        print("=" * 80)
        print("➕ ДОДАВАННЯ НОВИХ АГЕНТІВ")
        print("=" * 80)
        print()
        
        created_count = 0
        passwords = []
        
        for agent_data in agents_from_screenshot:
            username = agent_data['username']
            
            # Перевіряємо, чи вже існує
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"⚠️ {username:25} - вже існує, пропускаємо")
                continue
            
            # Генеруємо email
            email = f"{username}@pro-part.online"
            
            # Генеруємо пароль
            password = generate_password(12)
            
            # Створюємо агента
            new_agent = User(
                username=username,
                email=email,
                role=agent_data['role'],
                is_active=True,
                is_verified=False,
                created_at=datetime.utcnow()
            )
            new_agent.set_password(password)
            
            db.session.add(new_agent)
            
            passwords.append({
                'username': username,
                'email': email,
                'password': password,
                'role': agent_data['role']
            })
            
            print(f"✅ {username:25} - створено (email: {email}, пароль: {password})")
            created_count += 1
        
        # Зберігаємо всі зміни
        if created_count > 0:
            try:
                db.session.commit()
                print()
                print("=" * 80)
                print(f"✅ СТВОРЕНО: {created_count} нових агентів")
                print("=" * 80)
                print()
                
                # Зберігаємо паролі
                output_file = 'agents_passwords_reset.txt'
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write("ПАРОЛІ ДЛЯ АГЕНТІВ (ПІСЛЯ СКИДАННЯ)\n")
                    f.write("=" * 80 + "\n\n")
                    for item in passwords:
                        f.write(f"Логін: {item['username']}\n")
                        f.write(f"Email: {item['email']}\n")
                        f.write(f"Роль: {item['role']}\n")
                        f.write(f"Пароль: {item['password']}\n")
                        f.write("-" * 80 + "\n\n")
                
                print(f"📄 Паролі збережено у файл: {output_file}")
                print()
                
                # Виводимо таблицю
                print("=" * 80)
                print("📋 СТВОРЕНІ АГЕНТИ:")
                print("=" * 80)
                print(f"{'Логін':<25} {'Email':<40} {'Роль':<10} {'Пароль':<15}")
                print("-" * 80)
                for item in passwords:
                    print(f"{item['username']:<25} {item['email']:<40} {item['role']:<10} {item['password']:<15}")
                print("=" * 80)
                print()
                
                # Показуємо список всіх користувачів
                print("=" * 80)
                print("📋 ВСІ КОРИСТУВАЧІ В СИСТЕМІ:")
                print("=" * 80)
                all_users_final = User.query.order_by(User.role, User.username).all()
                print(f"{'ID':<5} {'Логін':<25} {'Email':<40} {'Роль':<10}")
                print("-" * 80)
                for user in all_users_final:
                    print(f"{user.id:<5} {user.username:<25} {user.email:<40} {user.role:<10}")
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
        reset_agents()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

