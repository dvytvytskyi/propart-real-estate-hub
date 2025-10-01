#!/usr/bin/env python3
"""
Скрипт для добавления новых пользователей в Real Estate Agents Hub
Использование: python add_user.py
"""

import sys
import getpass
from werkzeug.security import generate_password_hash
import psycopg2
from datetime import datetime

def add_user():
    print("👤 Добавление нового пользователя")
    print("=" * 40)
    
    # Получаем данные от пользователя
    username = input("Имя пользователя: ").strip()
    if not username:
        print("❌ Имя пользователя не может быть пустым")
        return False
    
    email = input("Email: ").strip()
    if not email or '@' not in email:
        print("❌ Введите корректный email")
        return False
    
    print("\nРоли:")
    print("1. admin - Администратор")
    print("2. agent - Агент")
    
    role_choice = input("Выберите роль (1 или 2): ").strip()
    if role_choice == '1':
        role = 'admin'
    elif role_choice == '2':
        role = 'agent'
    else:
        print("❌ Неверный выбор роли")
        return False
    
    password = getpass.getpass("Пароль: ")
    if len(password) < 6:
        print("❌ Пароль должен содержать минимум 6 символов")
        return False
    
    confirm_password = getpass.getpass("Подтвердите пароль: ")
    if password != confirm_password:
        print("❌ Пароли не совпадают")
        return False
    
    try:
        # Подключение к базе данных
        conn = psycopg2.connect('dbname=real_estate_agents')
        cur = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cur.execute('SELECT id FROM "user" WHERE username = %s OR email = %s', (username, email))
        existing_user = cur.fetchone()
        
        if existing_user:
            print("❌ Пользователь с таким именем или email уже существует")
            cur.close()
            conn.close()
            return False
        
        # Хешируем пароль
        password_hash = generate_password_hash(password)
        
        # Создаем нового пользователя
        cur.execute('''
            INSERT INTO "user" (username, email, password_hash, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (username, email, password_hash, role, True, datetime.now()))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n✅ Пользователь успешно создан!")
        print(f"👤 Имя пользователя: {username}")
        print(f"📧 Email: {email}")
        print(f"👑 Роль: {role}")
        print(f"🆔 ID: {user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании пользователя: {e}")
        return False

def list_users():
    """Показать всех пользователей"""
    try:
        conn = psycopg2.connect('dbname=real_estate_agents')
        cur = conn.cursor()
        
        cur.execute('SELECT id, username, email, role, is_active FROM "user" ORDER BY id')
        users = cur.fetchall()
        
        print("\n👥 Список пользователей:")
        print("=" * 60)
        print(f"{'ID':<3} {'Имя':<20} {'Email':<30} {'Роль':<10} {'Активен'}")
        print("-" * 60)
        
        for user in users:
            user_id, username, email, role, is_active = user
            status = "✅" if is_active else "❌"
            print(f"{user_id:<3} {username:<20} {email:<30} {role:<10} {status}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка пользователей: {e}")

if __name__ == "__main__":
    print("🏠 Real Estate Agents Hub - Управление пользователями")
    print("=" * 50)
    
    while True:
        print("\nВыберите действие:")
        print("1. Добавить нового пользователя")
        print("2. Показать всех пользователей")
        print("3. Выход")
        
        choice = input("\nВаш выбор (1-3): ").strip()
        
        if choice == '1':
            add_user()
        elif choice == '2':
            list_users()
        elif choice == '3':
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
