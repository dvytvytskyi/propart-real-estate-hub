#!/bin/bash

# Автоматичний скрипт для оновлення коду, видалення лідів та перезапуску
# НЕ ПОТРЕБУЄ ПІДТВЕРДЖЕННЯ! Використовуйте обережно!

set -e

echo "========================================"
echo "🚀 АВТОМАТИЧНИЙ DEPLOY & CLEANUP"
echo "========================================"
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# 1. Git pull
echo "1️⃣ Оновлення коду..."
git pull origin main
echo "✅ Код оновлено"
echo ""

# 2. Видалення лідів (автоматично)
echo "2️⃣ Видалення лідів..."
venv/bin/python3 << 'PYTHON_SCRIPT'
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app import app, db, Lead

with app.app_context():
    total = Lead.query.count()
    print(f"   Знайдено лідів: {total}")
    
    if total > 0:
        Lead.query.delete()
        db.session.commit()
        print(f"   ✅ Видалено {total} лідів")
    else:
        print("   ✅ Лідів немає")
    
    remaining = Lead.query.count()
    print(f"   Залишилося: {remaining}")
PYTHON_SCRIPT

echo ""

# 3. Перезапуск
echo "3️⃣ Перезапуск додатку..."
pkill -f "python.*run.py" 2>/dev/null || true
sleep 2

nohup venv/bin/python run.py > logs/propart.log 2>&1 &
sleep 4

# 4. Статус
echo ""
echo "4️⃣ Перевірка:"
if ps aux | grep "python.*run.py" | grep -v grep > /dev/null; then
    echo "   ✅ Додаток працює"
    ps aux | grep "python.*run.py" | grep -v grep | awk '{print "   PID:", $2, "RAM:", $6/1024 "MB"}'
else
    echo "   ❌ Додаток НЕ запущений!"
    tail -20 logs/propart.log
    exit 1
fi

if netstat -tulpn 2>/dev/null | grep -q 8090; then
    echo "   ✅ Порт 8090 відкритий"
else
    echo "   ❌ Порт 8090 закритий!"
fi

echo ""
echo "========================================"
echo "✅ DEPLOY ЗАВЕРШЕНО!"
echo "========================================"
echo ""
echo "🌐 https://agent.pro-part.online"
echo ""

