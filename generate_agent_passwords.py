#!/usr/bin/env python3
"""
Генерація паролів для нових агентів
Цей скрипт генерує паролі навіть без підключення до БД
"""

import secrets
import string

def generate_password(length=12):
    """Генерує безпечний випадковий пароль"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Нові агенти
new_agents = [
    {'username': 'hatamatata'},
    {'username': 'yanina_d'},
    {'username': 'o_antipenko'},
    {'username': 'ideal_home'},
    {'username': 'gorzhiy'},
    {'username': 'l_bogdanenko'},
]

print("=" * 80)
print("🔧 ГЕНЕРАЦІЯ ПАРОЛІВ ДЛЯ НОВИХ АГЕНТІВ")
print("=" * 80)
print()

passwords = []

for agent_data in new_agents:
    username = agent_data['username']
    email = f"{username}@pro-part.online"
    password = generate_password(12)
    
    passwords.append({
        'username': username,
        'email': email,
        'password': password
    })

# Зберігаємо паролі
output_file = 'new_agents_passwords.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("ПАРОЛІ ДЛЯ НОВИХ АГЕНТІВ\n")
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
print("📋 ПАРОЛІ ДЛЯ НОВИХ АГЕНТІВ:")
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

