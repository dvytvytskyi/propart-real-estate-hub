#!/bin/bash

# Оновлення DATABASE_URL з правильними credentials
echo "🔄 Оновлення DATABASE_URL..."

# Зупиняємо Gunicorn
pkill -f gunicorn
sleep 2

# Оновлюємо .env файл
sed -i 's/DATABASE_URL=postgresql:\/\/propart:.*@127.0.0.1:5432\/realestateagents/DATABASE_URL=postgresql:\/\/pro-part-agent:WMS5hNiYrNQlhepbn1g8@127.0.0.1:5432\/realestateagents/' .env

# Перевіряємо оновлення
echo "📋 Новий DATABASE_URL:"
grep DATABASE_URL .env

# Тестуємо підключення до БД
echo "🔍 Тестування підключення до БД..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5432,
        user='pro-part-agent',
        password='WMS5hNiYrNQlhepbn1g8',
        database='realestateagents'
    )
    print('✅ Підключення до БД успішне!')
    conn.close()
except Exception as e:
    print(f'❌ Помилка підключення: {e}')
"

# Запускаємо setup.py для створення таблиць
echo "🏗️ Створення таблиць БД..."
python3 setup.py

# Запускаємо Gunicorn
echo "🚀 Запуск Gunicorn..."
gunicorn --bind 127.0.0.1:8090 --workers 3 --timeout 120 --access-logfile logs/access.log --error-logfile logs/error.log --log-level info wsgi:application &

echo "✅ Оновлення завершено!"
echo "🌐 Сайт доступний: http://agent.pro-part.online"
