#!/bin/bash

# ============================================================
# 🚀 ЗАПУСК PROPART НА СЕРВЕРІ
# ============================================================

echo "============================================================"
echo "🚀 ЗАПУСК PROPART REAL ESTATE HUB"
echo "============================================================"
echo ""

# ============================================================
# КРОК 1: ПОШУК ПРОЕКТУ
# ============================================================

echo "1️⃣ Шукаю проект..."
PROJECT_PATH=$(find /home /var/www /opt -name "propart-real-estate-hub" -type d 2>/dev/null | head -1)

if [ -z "$PROJECT_PATH" ]; then
    echo "❌ Проект не знайдено!"
    echo ""
    echo "Спробуйте вручну:"
    echo "  find /home -name '*propart*' -type d 2>/dev/null"
    exit 1
fi

echo "✅ Знайдено: $PROJECT_PATH"
cd "$PROJECT_PATH"
echo ""

# ============================================================
# КРОК 2: ПЕРЕВІРКА GIT
# ============================================================

echo "2️⃣ Перевіряю git статус..."
git status | head -10
echo ""

echo "3️⃣ Отримую останні зміни..."
git pull origin main
echo ""

# ============================================================
# КРОК 3: ПЕРЕВІРКА .ENV
# ============================================================

echo "4️⃣ Перевіряю .env файл..."
if [ -f .env ]; then
    echo "✅ .env існує"
    if grep -q "^DATABASE_URL=" .env; then
        echo "✅ DATABASE_URL налаштовано"
    else
        echo "⚠️  DATABASE_URL відсутній"
    fi
else
    echo "❌ .env НЕ ЗНАЙДЕНО!"
fi
echo ""

# ============================================================
# КРОК 4: ЗУПИНКА СТАРИХ ПРОЦЕСІВ
# ============================================================

echo "5️⃣ Зупиняю старі процеси..."

# Gunicorn
if pgrep -f gunicorn > /dev/null; then
    echo "   Зупиняю gunicorn..."
    pkill -f gunicorn
    sleep 2
fi

# Python run.py
if pgrep -f "python.*run.py" > /dev/null; then
    echo "   Зупиняю python run.py..."
    pkill -f "python.*run.py"
    sleep 2
fi

# Systemd service
if systemctl is-active propart > /dev/null 2>&1; then
    echo "   Зупиняю systemd service..."
    systemctl stop propart
fi

echo "✅ Старі процеси зупинено"
echo ""

# ============================================================
# КРОК 5: ЗАПУСК ДОДАТКУ
# ============================================================

echo "6️⃣ Запускаю додаток..."
echo ""

# Спробувати через systemd
if [ -f /etc/systemd/system/propart.service ]; then
    echo "📦 Запуск через systemd..."
    systemctl start propart
    sleep 3
    systemctl status propart --no-pager | head -10
    
# Спробувати через gunicorn
elif [ -f gunicorn_config.py ]; then
    echo "📦 Запуск через gunicorn..."
    gunicorn --config gunicorn_config.py wsgi:app --daemon
    sleep 3
    
# Запуск через python run.py
else
    echo "📦 Запуск через python run.py..."
    nohup python3 run.py > logs/propart.log 2>&1 &
    sleep 3
fi

echo ""

# ============================================================
# КРОК 6: ПЕРЕВІРКА ЗАПУСКУ
# ============================================================

echo "7️⃣ Перевіряю запуск..."
echo ""

# Перевірка процесів
echo "🔍 Процеси:"
if ps aux | grep -E "gunicorn|python.*run.py" | grep -v grep > /dev/null; then
    echo "✅ Додаток запущений:"
    ps aux | grep -E "gunicorn|python.*run.py" | grep -v grep | head -3
else
    echo "❌ Додаток НЕ запущений!"
fi
echo ""

# Перевірка портів
echo "🔍 Порти:"
if netstat -tulpn 2>/dev/null | grep -E ":5001|:5000|:8000" > /dev/null; then
    echo "✅ Порт відкритий:"
    netstat -tulpn | grep -E ":5001|:5000|:8000"
else
    echo "⚠️  Порт не відкритий"
fi
echo ""

# Перевірка HTTP
echo "🔍 HTTP відповідь:"
if command -v curl > /dev/null; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/ 2>/dev/null)
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
        echo "✅ HTTP працює (статус: $HTTP_STATUS)"
    else
        echo "⚠️  HTTP статус: $HTTP_STATUS"
    fi
fi
echo ""

# Перевірка Nginx
echo "🔍 Nginx:"
if systemctl is-active nginx > /dev/null 2>&1; then
    echo "✅ Nginx запущений"
    
    # Перевірка конфігу домену
    if grep -r "agent.pro-part.online" /etc/nginx/sites-enabled/ > /dev/null 2>&1; then
        echo "✅ Конфіг домену активний"
    else
        echo "⚠️  Конфіг домену НЕ знайдено в sites-enabled"
    fi
else
    echo "⚠️  Nginx НЕ запущений"
    echo "   Запустіть: systemctl start nginx"
fi
echo ""

# Логи
echo "📄 Останні логи:"
if [ -f logs/propart.log ]; then
    tail -15 logs/propart.log
elif [ -f /var/log/propart/propart.log ]; then
    tail -15 /var/log/propart/propart.log
else
    journalctl -u propart -n 15 --no-pager 2>/dev/null || echo "Логи не знайдено"
fi

echo ""
echo "============================================================"
echo "✅ ЗАПУСК ЗАВЕРШЕНО!"
echo "============================================================"
echo ""
echo "🌐 Перевірте сайт:"
echo "   http://agent.pro-part.online"
echo "   https://agent.pro-part.online"
echo ""

