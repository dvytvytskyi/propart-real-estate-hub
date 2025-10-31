#!/bin/bash

# Цей скрипт автоматично виправляє помилку 502 на сервері

echo "🔧 АВТОМАТИЧНЕ ВИПРАВЛЕННЯ ПОМИЛКИ 502"
echo "=========================================="
echo ""

# 1. Перевірка поточної директорії
if [ ! -d "/var/www/propart" ]; then
    echo "❌ Директорія /var/www/propart не знайдена"
    echo "Створюємо структуру..."
    sudo mkdir -p /var/www/propart
    cd /var/www
    
    # Клонуємо репозиторій якщо його немає
    if [ ! -f "/var/www/propart/app.py" ]; then
        echo "⬇️ Клонування репозиторію..."
        # Тут потрібно буде вказати ваш GitHub репозиторій
        echo "❌ Репозиторій не знайдено. Потрібно спочатку задеплоїти проект."
        exit 1
    fi
fi

cd /var/www/propart

echo "✅ Знаходжусь в /var/www/propart"
echo ""

# 2. Оновлення коду
echo "📥 Крок 1: Оновлення коду з GitHub"
echo "--------------------------------------"
git stash 2>/dev/null
git pull origin main
if [ $? -eq 0 ]; then
    echo "✅ Код оновлено"
else
    echo "⚠️ Git pull не вдався, продовжую з поточним кодом..."
fi
echo ""

# 3. Перевірка статусу сервісів
echo "📊 Крок 2: Перевірка поточного статусу"
echo "--------------------------------------"
echo "PostgreSQL: $(sudo systemctl is-active postgresql 2>/dev/null || echo 'inactive')"
echo "ProPart: $(sudo systemctl is-active propart 2>/dev/null || echo 'inactive')"
echo "Nginx: $(sudo systemctl is-active nginx 2>/dev/null || echo 'inactive')"
echo ""

# 4. Зупинка всіх процесів Gunicorn
echo "🛑 Крок 3: Зупинка Gunicorn"
echo "--------------------------------------"
GUNICORN_PIDS=$(ps aux | grep gunicorn | grep -v grep | awk '{print $2}')
if [ ! -z "$GUNICORN_PIDS" ]; then
    echo "Знайдено процесів Gunicorn: $(echo $GUNICORN_PIDS | wc -w)"
    sudo pkill -9 gunicorn 2>/dev/null
    sleep 2
    echo "✅ Всі процеси Gunicorn зупинено"
else
    echo "ℹ️ Gunicorn процеси не знайдені"
fi
echo ""

# 5. Перезапуск PostgreSQL
echo "🔄 Крок 4: Перезапуск PostgreSQL"
echo "--------------------------------------"
sudo systemctl restart postgresql
sleep 3
PG_STATUS=$(sudo systemctl is-active postgresql)
echo "PostgreSQL: $PG_STATUS"
if [ "$PG_STATUS" != "active" ]; then
    echo "❌ PostgreSQL не запустився!"
    sudo systemctl status postgresql --no-pager -l
fi
echo ""

# 6. Перевірка бази даних
echo "🗄️ Крок 5: Перевірка бази даних"
echo "--------------------------------------"
sudo -u postgres psql -d real_estate_agents -c "SELECT COUNT(*) FROM users;" 2>&1 | head -5
if [ $? -eq 0 ]; then
    echo "✅ База даних доступна"
else
    echo "⚠️ Проблема з базою даних"
fi
echo ""

# 7. Перезапуск ProPart (Gunicorn)
echo "🔄 Крок 6: Перезапуск ProPart"
echo "--------------------------------------"
sudo systemctl restart propart
sleep 5

PROPART_STATUS=$(sudo systemctl is-active propart)
echo "ProPart: $PROPART_STATUS"

if [ "$PROPART_STATUS" != "active" ]; then
    echo "❌ ProPart не запустився!"
    echo ""
    echo "📋 Останні 30 рядків логів:"
    sudo journalctl -u propart -n 30 --no-pager
    echo ""
    echo "📋 Gunicorn error log:"
    sudo tail -30 /var/log/propart/gunicorn_error.log 2>/dev/null || echo "Лог не знайдено"
    exit 1
else
    echo "✅ ProPart запущено"
fi
echo ""

# 8. Перевірка процесів Gunicorn
echo "⚙️ Крок 7: Перевірка процесів Gunicorn"
echo "--------------------------------------"
sleep 2
GUNICORN_COUNT=$(ps aux | grep gunicorn | grep -v grep | wc -l)
echo "Запущено процесів: $GUNICORN_COUNT"
if [ $GUNICORN_COUNT -gt 0 ]; then
    echo "✅ Gunicorn працює"
    ps aux | grep gunicorn | grep -v grep | head -3
else
    echo "❌ Gunicorn не запущено!"
fi
echo ""

# 9. Перевірка порту 8000
echo "🔌 Крок 8: Перевірка порту 8000"
echo "--------------------------------------"
sudo netstat -tlnp | grep :8000
if [ $? -eq 0 ]; then
    echo "✅ Порт 8000 слухається"
else
    echo "❌ Нічого не слухає на порту 8000"
fi
echo ""

# 10. Перезапуск Nginx
echo "🔄 Крок 9: Перезапуск Nginx"
echo "--------------------------------------"
sudo systemctl restart nginx
sleep 2
NGINX_STATUS=$(sudo systemctl is-active nginx)
echo "Nginx: $NGINX_STATUS"
if [ "$NGINX_STATUS" != "active" ]; then
    echo "❌ Nginx не запустився!"
    sudo systemctl status nginx --no-pager
else
    echo "✅ Nginx запущено"
fi
echo ""

# 11. Тест веб-сервера
echo "🌐 Крок 10: Тест веб-сервера"
echo "--------------------------------------"
HTTP_LOCAL=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null)
echo "HTTP localhost:8000 → $HTTP_LOCAL"

if [ "$HTTP_LOCAL" = "200" ] || [ "$HTTP_LOCAL" = "302" ] || [ "$HTTP_LOCAL" = "301" ]; then
    echo "✅ Локальний веб-сервер відповідає"
else
    echo "⚠️ Локальний веб-сервер не відповідає (код: $HTTP_LOCAL)"
fi
echo ""

# 12. Підсумок
echo "=========================================="
echo "📊 ПІДСУМОК"
echo "=========================================="
echo ""
echo "Статус сервісів:"
echo "  🐘 PostgreSQL: $(sudo systemctl is-active postgresql)"
echo "  🦄 ProPart:    $(sudo systemctl is-active propart)"
echo "  🌐 Nginx:      $(sudo systemctl is-active nginx)"
echo ""
echo "Процеси:"
echo "  ⚙️ Gunicorn:   $GUNICORN_COUNT процесів"
echo ""
echo "Веб-сервер:"
echo "  🌐 HTTP Code:  $HTTP_LOCAL"
echo ""

# 13. Фінальна перевірка
ALL_OK=true
if [ "$(sudo systemctl is-active postgresql)" != "active" ]; then ALL_OK=false; fi
if [ "$(sudo systemctl is-active propart)" != "active" ]; then ALL_OK=false; fi
if [ "$(sudo systemctl is-active nginx)" != "active" ]; then ALL_OK=false; fi

if [ "$ALL_OK" = true ]; then
    echo "=========================================="
    echo "✅ ВСЕ ПРАЦЮЄ!"
    echo "=========================================="
    echo ""
    echo "🎉 Сайт має працювати!"
    echo ""
    echo "📌 Відкрийте в браузері:"
    echo "   https://agent.pro-part.online"
    echo "   https://agent.pro-part.online/admin/users"
    echo ""
else
    echo "=========================================="
    echo "⚠️ Є ПРОБЛЕМИ"
    echo "=========================================="
    echo ""
    echo "Для детальної діагностики виконайте:"
    echo "  sudo journalctl -u propart -n 100 --no-pager"
    echo ""
fi

echo "📋 Для моніторингу логів в реальному часі:"
echo "   sudo journalctl -u propart -f"
echo ""

