#!/bin/bash

# Скрипт для оновлення статусів на сервері agent.pro-part.online

echo "🚀 Оновлення статусів на сервері..."
echo ""

# Шлях до проекту на сервері
PROJECT_PATH="/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub"

cd "$PROJECT_PATH" || {
    echo "❌ Помилка: не вдалося перейти в $PROJECT_PATH"
    exit 1
}

# 1. Git pull
echo "1️⃣ Оновлення коду з Git..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Помилка при git pull"
    exit 1
fi
echo "✅ Код оновлено"
echo ""

# 2. Перезапуск додатку через systemd (якщо доступний)
echo "2️⃣ Перезапуск додатку..."
if systemctl is-active --quiet propart 2>/dev/null; then
    sudo systemctl restart propart
    sleep 3
    if systemctl is-active --quiet propart; then
        echo "✅ Додаток перезапущено через systemd"
    else
        echo "❌ Помилка перезапуску через systemd"
        sudo systemctl status propart --no-pager -l | head -20
    fi
elif [ -f "venv/bin/python" ]; then
    # Якщо запущено через nohup
    pkill -f "python.*run.py" 2>/dev/null || true
    sleep 2
    nohup venv/bin/python run.py > logs/propart.log 2>&1 &
    sleep 2
    if ps aux | grep "python.*run.py" | grep -v grep > /dev/null; then
        echo "✅ Додаток перезапущено"
    else
        echo "❌ Помилка перезапуску додатку"
    fi
else
    echo "⚠️ Не вдалося визначити спосіб запуску додатку"
fi
echo ""

# 3. Перезапуск Nginx для оновлення статичних файлів
echo "3️⃣ Перезапуск Nginx..."
if systemctl is-active --quiet nginx 2>/dev/null; then
    sudo systemctl reload nginx || sudo systemctl restart nginx
    sleep 2
    if systemctl is-active --quiet nginx; then
        echo "✅ Nginx перезапущено"
    else
        echo "❌ Помилка перезапуску Nginx"
    fi
else
    echo "⚠️ Nginx не запущений"
fi
echo ""

# 4. Перевірка статусу
echo "4️⃣ Перевірка статусу..."
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8090 > /dev/null 2>&1 || \
   curl -s -o /dev/null -w "%{http_code}" https://agent.pro-part.online > /dev/null 2>&1; then
    echo "✅ Додаток працює"
else
    echo "⚠️ Перевірте логи: tail -f logs/propart.log"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Оновлення завершено!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Відкрийте: https://agent.pro-part.online/dashboard"
echo ""
echo "💡 Не забудьте очистити кеш браузера (Ctrl+Shift+R)"
echo ""

