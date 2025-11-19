#!/bin/bash

# Скрипт для деплою виправлення синхронізації коментарів з HubSpot

echo "🚀 Деплой виправлення синхронізації коментарів з HubSpot..."
echo ""

# Шлях до проекту на сервері
PROJECT_PATH="/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub"

# Перевірка чи є зміни для коміту
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Є незбережені зміни. Комічуємо..."
    git add app.py
    git commit -m "Виправлено синхронізацію коментарів з HubSpot: покращено логування та обробку помилок"
    echo "✅ Зміни закомічено"
    echo ""
fi

# Push змін
echo "📤 Відправка змін на сервер..."
git push origin main
if [ $? -ne 0 ]; then
    echo "❌ Помилка при git push"
    exit 1
fi
echo "✅ Зміни відправлено"
echo ""

# SSH команди для оновлення на сервері
echo "🔄 Оновлення на сервері..."
ssh pro-part-agent@agent.pro-part.online << 'ENDSSH'
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

echo "1️⃣ Git pull..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Помилка при git pull"
    exit 1
fi
echo "✅ Код оновлено"
echo ""

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
ENDSSH

echo ""
echo "✅ Деплой завершено!"
echo ""
echo "🌐 Відкрийте: https://agent.pro-part.online"
echo ""
echo "💡 Перевірте логи після додавання коментаря:"
echo "   ssh pro-part-agent@agent.pro-part.online 'tail -f /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/logs/propart.log'"
echo ""

