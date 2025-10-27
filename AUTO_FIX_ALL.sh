#!/bin/bash
# ════════════════════════════════════════════════════════════════
# 🔧 АВТОМАТИЧНЕ ВИПРАВЛЕННЯ ВСІХ ПРОБЛЕМ
# ════════════════════════════════════════════════════════════════

set -e

echo "════════════════════════════════════════════════════════════"
echo "🔧 АВТОМАТИЧНЕ ВИПРАВЛЕННЯ"
echo "════════════════════════════════════════════════════════════"
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# Зупинити все
echo "🛑 Зупинка процесів..."
pkill -f "python.*run.py" 2>/dev/null || true
sleep 2

# Git pull
echo "📥 Оновлення коду..."
git pull origin main

# Перевірити venv
if [ ! -d "venv" ]; then
    echo "📦 Створення venv..."
    python3 -m venv venv
fi

echo "📦 Оновлення залежностей..."
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt

# Міграція БД з обробкою помилок
echo "🔄 Міграція БД..."
venv/bin/python3 << 'ENDPYTHON'
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app import app, db

with app.app_context():
    try:
        # Створити всі таблиці
        db.create_all()
        print("✅ Таблиці створено/оновлено")
        
        # Перевірити чи є колонка admin_id
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('user')]
        
        if 'admin_id' in columns:
            print("✅ Колонка admin_id існує")
        else:
            print("⚠️  Колонка admin_id відсутня - додаю...")
            db.engine.execute('ALTER TABLE user ADD COLUMN admin_id INTEGER REFERENCES user(id)')
            print("✅ Колонка admin_id додана")
            
    except Exception as e:
        print(f"⚠️  Помилка міграції (ігноруємо): {e}")
ENDPYTHON

# Створити адмінів
echo "👤 Створення адмінів..."
venv/bin/python3 << 'ENDPYTHON'
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    try:
        admins = [
            ('anton_admin', 'anton@pro-part.online', 'sfajerfe234ewqf#'),
            ('alex_admin', 'alex@pro-part.online', 'dgerifwef@fmso4'),
        ]
        
        for username, email, password in admins:
            existing = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if not existing:
                admin = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role='admin',
                    is_verified=True
                )
                db.session.add(admin)
                print(f"  ✅ {username}")
            else:
                print(f"  ⚠️  {username} існує")
        
        db.session.commit()
        
        total = User.query.filter_by(role='admin').count()
        print(f"\n✅ Адмінів: {total}")
        
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
ENDPYTHON

# Запуск
echo ""
echo "🚀 Запуск додатку..."
nohup venv/bin/python run.py > logs/propart.log 2>&1 &
sleep 5

# Перевірка
echo ""
echo "════════════════════════════════════════════════════════════"
echo "📊 РЕЗУЛЬТАТ:"
echo "════════════════════════════════════════════════════════════"

if ps aux | grep "python.*run.py" | grep -v grep > /dev/null; then
    echo "✅ Додаток працює"
    ps aux | grep "python.*run.py" | grep -v grep | awk '{print "   PID:", $2}'
else
    echo "❌ Додаток НЕ працює"
fi

if netstat -tulpn 2>/dev/null | grep -q 8090; then
    echo "✅ Порт 8090 відкритий"
else
    echo "❌ Порт 8090 закритий"
fi

echo ""
echo "📄 Логи (останні 20 рядків):"
tail -20 logs/propart.log

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🌐 Перевірте: https://agent.pro-part.online/register"
echo "════════════════════════════════════════════════════════════"

