#!/bin/bash

# Оновлення та перевірка сервера
# Використання: ./update_server.sh

SERVER_IP="188.245.228.175"
SERVER_USER="root"
SERVER_PASS="7NdMqCMV4wtw"
PROJECT_DIR="/home/pro-part-agent/htdocs/agent.pro-part.online"

echo "🔍 === ПІДКЛЮЧЕННЯ ДО СЕРВЕРА ==="
echo "IP: $SERVER_IP"
echo "User: $SERVER_USER"
echo ""

# Команди для виконання на сервері
COMMANDS="
cd $PROJECT_DIR
echo '📁 Поточна директорія:'
pwd
echo ''
echo '📊 Статус Git:'
git status
echo ''
echo '📥 Оновлення коду:'
git fetch origin
git pull origin main
echo ''
echo '🔍 Перевірка HUBSPOT_API_KEY:'
if [ -f .env ]; then
    echo 'Знайдено .env файл:'
    grep HUBSPOT .env || echo 'HUBSPOT_API_KEY не знайдено в .env'
else
    echo '⚠️ .env файл не знайдено'
fi
echo ''
echo '📋 Перевірка версії app.py:'
if grep -q 'def diagnostic' app.py 2>/dev/null; then
    echo '✅ Діагностичний ендпоінт знайдено в app.py'
else
    echo '❌ Діагностичний ендпоінт НЕ знайдено в app.py'
fi
echo ''
echo '🔧 Статус systemd сервісу (якщо є):'
systemctl status propart --no-pager 2>/dev/null || echo 'Сервіс propart не знайдено'
"

# Спробуємо використати sshpass якщо є
if command -v sshpass &> /dev/null; then
    echo "Використовую sshpass для підключення..."
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "$COMMANDS"
else
    echo "⚠️ sshpass не встановлено. Виконайте команди вручну:"
    echo ""
    echo "ssh $SERVER_USER@$SERVER_IP"
    echo ""
    echo "Потім виконайте ці команди:"
    echo "$COMMANDS"
fi

