#!/bin/bash

# Скрипт для оновлення коду, видалення лідів та перезапуску на продакшн сервері
# Використання: bash deploy_and_cleanup.sh

set -e  # Вийти при помилці

echo "========================================"
echo "🚀 DEPLOY & CLEANUP"
echo "========================================"
echo ""

# Перейти до директорії проекту
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# 1. Оновити код з Git
echo "1️⃣ Оновлення коду з GitHub..."
git pull origin main
echo "✅ Код оновлено"
echo ""

# 2. Видалити всіх лідів
echo "2️⃣ Видалення всіх лідів..."
echo "⚠️  УВАГА! Всі ліди будуть видалені!"
read -p "Продовжити? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    venv/bin/python3 delete_all_leads.py
    echo "✅ Ліди видалено"
else
    echo "❌ Видалення скасовано"
fi
echo ""

# 3. Перезапустити додаток
echo "3️⃣ Перезапуск додатку..."
pkill -f "python.*run.py" || echo "Старих процесів не знайдено"
sleep 2

nohup venv/bin/python run.py > logs/propart.log 2>&1 &
sleep 4

# 4. Перевірити статус
echo ""
echo "4️⃣ Перевірка статусу..."
if ps aux | grep "python.*run.py" | grep -v grep > /dev/null; then
    echo "✅ Додаток запущено"
    ps aux | grep "python.*run.py" | grep -v grep | head -2
else
    echo "❌ Додаток НЕ запущений!"
    echo "Логи:"
    tail -20 logs/propart.log
    exit 1
fi

# 5. Перевірити порт
echo ""
if netstat -tulpn | grep 8090 > /dev/null; then
    echo "✅ Порт 8090 відкритий"
else
    echo "❌ Порт 8090 НЕ відкритий!"
fi

echo ""
echo "========================================"
echo "✅ ГОТОВО!"
echo "========================================"
echo ""
echo "🌐 Перевірте: https://agent.pro-part.online"
echo ""

