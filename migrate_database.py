#!/usr/bin/env python3
"""
Скрипт для міграції бази даних - додавання нових полів для геймифікації та верифікації
"""

import os
import sys
from datetime import datetime

# Додаємо поточну директорію до шляху Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def migrate_database():
    """Міграція бази даних"""
    with app.app_context():
        try:
            print("🔄 Початок міграції бази даних...")
            
            # Перевіряємо, чи існують нові поля
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            new_fields = [
                'points', 'level', 'total_leads', 'closed_deals',
                'is_verified', 'verification_requested', 'verification_request_date',
                'verification_document_path', 'verification_notes'
            ]
            
            missing_fields = [field for field in new_fields if field not in columns]
            
            if not missing_fields:
                print("✅ Всі нові поля вже існують в базі даних")
                return
            
            print(f"📝 Додаємо нові поля: {', '.join(missing_fields)}")
            
            # Додаємо нові поля через SQL ALTER TABLE
            for field in missing_fields:
                if field == 'points':
                    db.engine.execute('ALTER TABLE user ADD COLUMN points INTEGER DEFAULT 0')
                elif field == 'level':
                    db.engine.execute('ALTER TABLE user ADD COLUMN level VARCHAR(20) DEFAULT "bronze"')
                elif field == 'total_leads':
                    db.engine.execute('ALTER TABLE user ADD COLUMN total_leads INTEGER DEFAULT 0')
                elif field == 'closed_deals':
                    db.engine.execute('ALTER TABLE user ADD COLUMN closed_deals INTEGER DEFAULT 0')
                elif field == 'is_verified':
                    db.engine.execute('ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0')
                elif field == 'verification_requested':
                    db.engine.execute('ALTER TABLE user ADD COLUMN verification_requested BOOLEAN DEFAULT 0')
                elif field == 'verification_request_date':
                    db.engine.execute('ALTER TABLE user ADD COLUMN verification_request_date DATETIME')
                elif field == 'verification_document_path':
                    db.engine.execute('ALTER TABLE user ADD COLUMN verification_document_path VARCHAR(200)')
                elif field == 'verification_notes':
                    db.engine.execute('ALTER TABLE user ADD COLUMN verification_notes TEXT')
                
                print(f"✅ Додано поле: {field}")
            
            # Оновлюємо рівні для існуючих користувачів
            users = User.query.all()
            for user in users:
                user.update_level()
                print(f"🔄 Оновлено рівень для користувача {user.username}: {user.level}")
            
            db.session.commit()
            print("✅ Міграція завершена успішно!")
            
        except Exception as e:
            print(f"❌ Помилка міграції: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_database()
