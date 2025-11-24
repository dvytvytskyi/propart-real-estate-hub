#!/usr/bin/env python3
"""
Експорт всіх користувачів з бази даних для аналізу
"""

import os
import sys
import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime)

def export_all_users():
    """Експортує всіх користувачів з БД"""
    with app.app_context():
        all_users = User.query.order_by(User.id).all()
        
        users_data = []
        for user in all_users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'is_verified': user.is_verified if hasattr(user, 'is_verified') else None,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            })
        
        # Зберігаємо в JSON
        output_file = 'exported_users.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'total_users': len(users_data),
                'users': users_data
            }, f, indent=2, ensure_ascii=False)
        
        print("=" * 80)
        print("📊 ЕКСПОРТ КОРИСТУВАЧІВ З БД")
        print("=" * 80)
        print(f"Експортовано: {len(users_data)} користувачів")
        print(f"Файл: {output_file}")
        print()
        print("Список користувачів:")
        print("-" * 80)
        for user in users_data:
            print(f"ID: {user['id']:<5} | {user['username']:<25} | {user['email']:<40} | {user['role']:<10}")

if __name__ == '__main__':
    try:
        export_all_users()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

