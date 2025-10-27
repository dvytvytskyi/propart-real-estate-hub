#!/bin/bash

# ============================================================
# 🚀 ПОВНИЙ ДЕПЛОЙ PROPART REAL ESTATE HUB
# ============================================================

echo "============================================================"
echo "🚀 ПОВНИЙ ДЕПЛОЙ PROPART REAL ESTATE HUB"
echo "============================================================"
echo ""

# ============================================================
# КРОК 1: ПІДКЛЮЧЕННЯ ДО СЕРВЕРА
# ============================================================
echo "📋 КРОК 1: Підключення до сервера"
echo "============================================================"
echo ""
echo "Виконайте на ЛОКАЛЬНОМУ комп'ютері:"
echo ""
echo "  ssh root@188.245.228.175"
echo ""
echo "Після підключення виконайте наступні команди на СЕРВЕРІ:"
echo ""
read -p "Натисніть Enter коли підключитеся до сервера..."

# ============================================================
# КРОК 2: ПОШУК ПРОЕКТУ
# ============================================================
echo ""
echo "============================================================"
echo "📋 КРОК 2: Пошук проекту на сервері"
echo "============================================================"
echo ""
echo "Виконайте на СЕРВЕРІ:"
echo ""
echo "  find /home -type d -name '*propart*' 2>/dev/null | head -10"
echo ""
echo "АБО:"
echo ""
echo "  ls -la /home/*/htdocs/"
echo ""
echo "Знайдіть шлях до проекту та замініть нижче:"
echo ""
read -p "Введіть шлях до проекту (наприклад /home/propart/htdocs/propart-real-estate-hub): " PROJECT_PATH

if [ -z "$PROJECT_PATH" ]; then
    echo "❌ Шлях не вказаний!"
    exit 1
fi

echo ""
echo "✅ Використовуємо шлях: $PROJECT_PATH"
echo ""

# ============================================================
# КОМАНДИ ДЛЯ ВИКОНАННЯ НА СЕРВЕРІ
# ============================================================

cat << 'SERVER_COMMANDS'

============================================================
📋 ВИКОНАЙТЕ ЦІ КОМАНДИ НА СЕРВЕРІ:
============================================================

# ============================================================
# КРОК 3: ПЕРЕХІД ДО ПРОЕКТУ
# ============================================================

cd /home/propart/htdocs/propart-real-estate-hub
# (замініть шлях на ваш, який знайшли вище)

pwd
# Має показати шлях до проекту


# ============================================================
# КРОК 4: ПЕРЕВІРКА GIT СТАТУСУ
# ============================================================

git status
git branch
# Переконайтеся що ви на гілці main


# ============================================================
# КРОК 5: ОТРИМАННЯ ОСТАННІХ ЗМІН
# ============================================================

git fetch origin
git pull origin main

# Має з'явитися:
# ✅ Already up to date
# АБО
# ✅ Updating ...
#    Fast-forward
#    app.py | ... insertions(+), ... deletions(-)


# ============================================================
# КРОК 6: СТВОРЕННЯ НОВИХ АДМІНІСТРАТОРІВ
# ============================================================

python3 << 'EOF'
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    print("👥 Створюю нових адміністраторів...")
    print()
    
    # Anton Admin
    existing_anton = User.query.filter_by(username='anton_admin').first()
    if not existing_anton:
        anton = User(
            username='anton_admin',
            email='anton@propart.com',
            password_hash=generate_password_hash('sfajerfe234ewqf#'),
            role='admin',
            is_verified=True
        )
        db.session.add(anton)
        print("✅ anton_admin створено")
    else:
        print("ℹ️  anton_admin вже існує")
    
    # Alex Admin
    existing_alex = User.query.filter_by(username='alex_admin').first()
    if not existing_alex:
        alex = User(
            username='alex_admin',
            email='alex@propart.com',
            password_hash=generate_password_hash('dgerifwef@fmso4'),
            role='admin',
            is_verified=True
        )
        db.session.add(alex)
        print("✅ alex_admin створено")
    else:
        print("ℹ️  alex_admin вже існує")
    
    db.session.commit()
    
    print()
    print("=" * 60)
    print("📋 ВСІ АДМІНІСТРАТОРИ:")
    print("=" * 60)
    admins = User.query.filter_by(role='admin').all()
    for admin in admins:
        print(f"   ✅ {admin.username} ({admin.email})")
    print()
EOF


# ============================================================
# КРОК 7: ПЕРЕВІРКА .ENV ФАЙЛУ
# ============================================================

echo ""
echo "🔍 Перевіряю .env файл..."
if [ -f .env ]; then
    echo "✅ .env файл існує"
    
    # Перевірка DATABASE_URL
    if grep -q "^DATABASE_URL=" .env; then
        echo "✅ DATABASE_URL налаштовано"
    else
        echo "⚠️  DATABASE_URL відсутній!"
    fi
    
    # Перевірка HUBSPOT_API_KEY
    if grep -q "^HUBSPOT_API_KEY=" .env; then
        echo "✅ HUBSPOT_API_KEY налаштовано"
    else
        echo "⚠️  HUBSPOT_API_KEY відсутній!"
    fi
    
    # Перевірка SECRET_KEY
    if grep -q "^SECRET_KEY=" .env; then
        echo "✅ SECRET_KEY налаштовано"
    else
        echo "⚠️  SECRET_KEY відсутній!"
    fi
else
    echo "❌ .env файл НЕ ЗНАЙДЕНО!"
    echo "Створіть .env файл на основі env_example.txt"
fi


# ============================================================
# КРОК 8: ПЕРЕЗАПУСК ДОДАТКУ
# ============================================================

echo ""
echo "============================================================"
echo "🔄 КРОК 8: Перезапуск додатку"
echo "============================================================"
echo ""

# ВАРІАНТ 1: Systemd service
if systemctl is-active propart > /dev/null 2>&1; then
    echo "🔄 Перезапуск через systemd..."
    systemctl restart propart
    sleep 3
    systemctl status propart --no-pager
    
# ВАРІАНТ 2: Docker
elif docker ps | grep -q propart; then
    echo "🔄 Перезапуск через Docker..."
    docker-compose restart
    
# ВАРІАНТ 3: Gunicorn процес
elif pgrep -f gunicorn > /dev/null; then
    echo "🔄 Перезапуск gunicorn..."
    pkill -f gunicorn
    sleep 2
    gunicorn --config gunicorn_config.py wsgi:app --daemon
    
# ВАРІАНТ 4: Python run.py
elif pgrep -f "python.*run.py" > /dev/null; then
    echo "🔄 Перезапуск python run.py..."
    pkill -f "python.*run.py"
    sleep 2
    nohup python run.py > logs/propart.log 2>&1 &
    
# ВАРІАНТ 5: CloudPanel (якщо встановлено clpctl)
elif command -v clpctl > /dev/null; then
    echo "🔄 Перезапуск через CloudPanel..."
    echo "Введіть домен сайту (наприклад: propart.example.com):"
    read DOMAIN
    if [ ! -z "$DOMAIN" ]; then
        clpctl site:restart:$DOMAIN
    fi
    
else
    echo "⚠️  Автоматичний перезапуск не вдався"
    echo ""
    echo "Виберіть спосіб перезапуску вручну:"
    echo ""
    echo "1. Systemd:"
    echo "   systemctl restart propart"
    echo ""
    echo "2. Docker:"
    echo "   docker-compose restart"
    echo ""
    echo "3. Gunicorn:"
    echo "   pkill -f gunicorn"
    echo "   gunicorn --config gunicorn_config.py wsgi:app --daemon"
    echo ""
    echo "4. Python:"
    echo "   pkill -f 'python.*run.py'"
    echo "   nohup python run.py > logs/propart.log 2>&1 &"
fi


# ============================================================
# КРОК 9: ПЕРЕВІРКА ДЕПЛОЮ
# ============================================================

echo ""
echo "============================================================"
echo "✅ КРОК 9: Перевірка деплою"
echo "============================================================"
echo ""

# Перевірка процесів
echo "🔍 Перевірка процесів:"
if pgrep -f "gunicorn|python.*run.py|propart" > /dev/null; then
    echo "   ✅ Додаток працює"
    ps aux | grep -E "gunicorn|python.*run.py" | grep -v grep | head -3
else
    echo "   ❌ Додаток НЕ працює!"
fi

echo ""

# Перевірка портів
echo "🔍 Перевірка портів:"
if netstat -tulpn | grep -E ":5000|:5001|:8000" > /dev/null 2>&1; then
    echo "   ✅ Порт відкритий"
    netstat -tulpn | grep -E ":5000|:5001|:8000" | head -3
else
    echo "   ⚠️  Порт не знайдено"
fi

echo ""

# Перевірка HTTP
echo "🔍 Перевірка HTTP:"
if command -v curl > /dev/null; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/ 2>/dev/null)
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
        echo "   ✅ HTTP працює (статус: $HTTP_STATUS)"
    else
        echo "   ⚠️  HTTP статус: $HTTP_STATUS"
    fi
else
    echo "   ℹ️  curl не встановлено"
fi

echo ""

# Перевірка логів
echo "🔍 Останні логи:"
if [ -f logs/propart.log ]; then
    tail -10 logs/propart.log
elif [ -f /var/log/propart/propart.log ]; then
    tail -10 /var/log/propart/propart.log
else
    journalctl -u propart -n 10 --no-pager 2>/dev/null || echo "   Логи не знайдено"
fi


# ============================================================
# КРОК 10: ФІНАЛЬНА ІНФОРМАЦІЯ
# ============================================================

echo ""
echo "============================================================"
echo "🎉 ДЕПЛОЙ ЗАВЕРШЕНО!"
echo "============================================================"
echo ""
echo "📋 Інформація для доступу:"
echo ""
echo "👤 Нові адміністратори:"
echo ""
echo "   1. Anton Admin"
echo "      Username: anton_admin"
echo "      Password: sfajerfe234ewqf#"
echo ""
echo "   2. Alex Admin"
echo "      Username: alex_admin"
echo "      Password: dgerifwef@fmso4"
echo ""
echo "   3. Головний Admin"
echo "      Username: admin"
echo "      Password: admin123"
echo ""
echo "============================================================"
echo ""
echo "✅ Перевірте сайт у браузері:"
echo "   https://your-domain.com"
echo ""
echo "⚠️  Після перевірки змініть паролі адміністраторів!"
echo ""
echo "============================================================"

SERVER_COMMANDS

echo ""
echo "============================================================"
echo "📋 КОМАНДИ ГОТОВІ!"
echo "============================================================"
echo ""
echo "Скопіюйте команди вище та виконайте їх на сервері"
echo "після підключення через SSH."
echo ""

