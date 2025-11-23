#!/bin/bash

# Скрипт для автоматичного деплою на production сервер
# Використання: ./deploy_to_production.sh

SERVER_IP="188.245.228.175"
SERVER_USER="root"
SERVER_PASS="7NdMqCMV4wtw"
PROJECT_PATH="/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub"

echo "🚀 Деплой на production сервер"
echo "=================================="
echo "📍 Сервер: $SERVER_IP"
echo "📂 Проект: $PROJECT_PATH"
echo ""

# Перевірка чи є sshpass
if ! command -v sshpass &> /dev/null; then
    echo "❌ sshpass не встановлено"
    echo "Встановіть: brew install hudochenkov/sshpass/sshpass"
    exit 1
fi

# Перевірка чи є зміни для коміту
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️ У вас є незакомічені зміни!"
    echo "Хочете закомітити та запушити їх? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        git add -A
        git commit -m "Update: $(date +%Y-%m-%d_%H:%M:%S)"
        git push origin main
        echo "✅ Зміни закомічені та запушені"
    else
        echo "❌ Деплой скасовано"
        exit 1
    fi
fi

echo "📡 Підключення до сервера..."
echo ""

sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SERVER_USER@$SERVER_IP" << ENDSSH
    echo "✅ Підключено до сервера!"
    echo "📍 Hostname: \$(hostname)"
    echo ""
    
    cd $PROJECT_PATH
    
    echo "📂 Поточний стан git:"
    git status --short | head -5
    echo ""
    
    echo "⬇️ Оновлення з GitHub..."
    git stash push -m "Локальні зміни перед pull \$(date +%Y-%m-%d_%H:%M:%S)" 2>/dev/null
    git pull origin main
    
    if [ \$? -eq 0 ]; then
        echo ""
        echo "✅ Оновлено успішно!"
        echo ""
        echo "🔄 Перезапуск сервісу..."
        sudo systemctl restart propart
        sleep 2
        
        echo ""
        echo "📊 Статус сервісу:"
        sudo systemctl status propart --no-pager -l | head -10
        
        echo ""
        echo "✅ Деплой завершено успішно!"
    else
        echo "❌ Помилка при оновленні!"
        exit 1
    fi
ENDSSH

if [ \$? -eq 0 ]; then
    echo ""
    echo "✅ Деплой виконано успішно!"
else
    echo ""
    echo "❌ Помилка при деплої!"
    exit 1
fi

