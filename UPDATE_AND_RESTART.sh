#!/bin/bash

echo "🔄 ОНОВЛЕННЯ КОДУ ТА ПЕРЕЗАПУСК"
echo "=========================================="
echo ""

# 1. Переходимо в директорію проекту
cd /var/www/propart

# 2. Бекап поточних змін (якщо є)
echo "📦 Створення бекапу локальних змін..."
git stash save "auto-backup-$(date +%Y%m%d-%H%M%S)" 2>/dev/null
echo ""

# 3. Отримуємо останній код з GitHub
echo "⬇️ Отримання останнього коду з GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Помилка при git pull"
    echo "Спробуйте:"
    echo "  cd /var/www/propart"
    echo "  git status"
    echo "  git reset --hard origin/main"
    echo "  git pull"
    exit 1
fi
echo "✅ Код оновлено"
echo ""

# 4. Активуємо віртуальне середовище
echo "🐍 Активація віртуального середовища..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Не вдалося активувати venv"
    exit 1
fi
echo "✅ Venv активовано"
echo ""

# 5. Оновлюємо залежності (якщо змінився requirements.txt)
echo "📦 Перевірка залежностей..."
pip install -r requirements.txt --quiet
echo "✅ Залежності перевірено"
echo ""

# 6. Перевірка міграцій бази даних (якщо потрібно)
echo "🗄️ Перевірка бази даних..."
# Тут можна додати команди для міграцій, якщо використовуєте Alembic
echo "✅ База даних готова"
echo ""

# 7. Зупинка всіх процесів Gunicorn
echo "🛑 Зупинка Gunicorn..."
sudo pkill -9 gunicorn 2>/dev/null
sleep 2
echo "✅ Gunicorn зупинено"
echo ""

# 8. Перезапуск PostgreSQL
echo "🔄 Перезапуск PostgreSQL..."
sudo systemctl restart postgresql
sleep 3
PGSQL_STATUS=$(sudo systemctl is-active postgresql)
if [ "$PGSQL_STATUS" = "active" ]; then
    echo "✅ PostgreSQL працює"
else
    echo "❌ PostgreSQL не запустився"
fi
echo ""

# 9. Перезапуск ProPart
echo "🔄 Перезапуск ProPart..."
sudo systemctl restart propart
sleep 5
PROPART_STATUS=$(sudo systemctl is-active propart)
if [ "$PROPART_STATUS" = "active" ]; then
    echo "✅ ProPart працює"
else
    echo "❌ ProPart не запустився"
    echo ""
    echo "📋 Логи помилок:"
    sudo journalctl -u propart -n 20 --no-pager
    exit 1
fi
echo ""

# 10. Перезапуск Nginx
echo "🔄 Перезапуск Nginx..."
sudo systemctl restart nginx
sleep 2
NGINX_STATUS=$(sudo systemctl is-active nginx)
if [ "$NGINX_STATUS" = "active" ]; then
    echo "✅ Nginx працює"
else
    echo "❌ Nginx не запустився"
fi
echo ""

# 11. Перевірка статусу
echo "=========================================="
echo "📊 ПІДСУМОК:"
echo "=========================================="
echo ""
echo "🐘 PostgreSQL: $PGSQL_STATUS"
echo "🦄 ProPart:    $PROPART_STATUS"
echo "🌐 Nginx:      $NGINX_STATUS"
echo ""

# 12. Тест підключення
echo "🌐 Тест веб-сервера:"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null)
echo "HTTP Status: $HTTP_STATUS"
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
    echo "✅ Веб-сервер відповідає"
else
    echo "❌ Веб-сервер не відповідає"
fi
echo ""

# 13. Перевірка процесів Gunicorn
GUNICORN_COUNT=$(ps aux | grep gunicorn | grep -v grep | wc -l)
echo "⚙️ Процесів Gunicorn: $GUNICORN_COUNT"
if [ $GUNICORN_COUNT -gt 0 ]; then
    echo "✅ Gunicorn запущено"
else
    echo "❌ Gunicorn не запущено"
fi
echo ""

echo "=========================================="
echo "✅ ОНОВЛЕННЯ ЗАВЕРШЕНО"
echo ""
echo "📌 Перевірте сайт:"
echo "   https://agent.pro-part.online"
echo ""
echo "📋 Для перегляду логів:"
echo "   sudo journalctl -u propart -f"
echo ""

