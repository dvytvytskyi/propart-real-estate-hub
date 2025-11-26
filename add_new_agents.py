#!/usr/bin/env python3
"""
Створення нових агентів з паролями
"""

import os
import sys
import secrets
import string

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Імпортуємо з app.py
from app import app, db, User

def generate_password(length=12):
    """Генерує безпечний випадковий пароль"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_new_agents():
    """Створює нових агентів"""
    # Нові агенти з паролями
    new_agents = [
        {'username': 'hatamatata', 'password': 'cFE6w37nTsIH'},
        {'username': 'yanina_d', 'password': 'VJBggxGauUTJ'},
        {'username': 'o_antipenko', 'password': 'FVDvof4uuJ2F'},
        {'username': 'ideal_home', 'password': 'ro8Vt4oADdxs'},
        {'username': 'gorzhiy', 'password': 'N9yeZV3MUIQ8'},
        {'username': 'l_bogdanenko', 'password': 'CZ11QyUb8UID'},
    ]
    
    with app.app_context():
        print("=" * 80)
        print("🔧 СТВОРЕННЯ НОВИХ АГЕНТІВ")
        print("=" * 80)
        print()
        
        created_count = 0
        skipped_count = 0
        
        passwords = []
        
        for agent_data in new_agents:
            username = agent_data['username']
            
            # Перевіряємо, чи вже існує
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"⚠️ {username:25} - вже існує, пропускаємо")
                skipped_count += 1
                continue
            
            # Генеруємо email
            email = f"{username}@pro-part.online"
            
            # Використовуємо згенерований пароль або генеруємо новий
            password = agent_data.get('password', generate_password(12))
            
            # Створюємо агента
            new_agent = User(
                username=username,
                email=email,
                role='agent',
                is_active=True,
                is_verified=False
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
                output_file = 'new_agents_passwords.txt'
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
                print()
                
                # Виводимо паролі для копіювання
                print("=" * 80)
                print("📋 ПАРОЛІ ДЛЯ КОПІЮВАННЯ:")
                print("=" * 80)
                for item in passwords:
                    print(f"{item['username']:<25} | {item['password']}")
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
        create_new_agents()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

