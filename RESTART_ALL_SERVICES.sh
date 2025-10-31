#!/bin/bash

echo "🔄 ШВИДКИЙ ПЕРЕЗАПУСК ВСІХ СЕРВІСІВ"
echo "=========================================="
echo ""

# 1. Зупинити всі процеси Gunicorn
echo "🛑 Зупиняю всі процеси Gunicorn..."
sudo pkill -9 gunicorn 2>/dev/null
sleep 2
echo "✅ Gunicorn зупинено"
echo ""

# 2. Перезапуск PostgreSQL
echo "🔄 Перезапускаю PostgreSQL..."
sudo systemctl restart postgresql
sleep 3
PGSQL_STATUS=$(sudo systemctl is-active postgresql)
if [ "$PGSQL_STATUS" = "active" ]; then
    echo "✅ PostgreSQL запущено"
else
    echo "❌ PostgreSQL не запустився: $PGSQL_STATUS"
fi
echo ""

# 3. Перезапуск ProPart (Gunicorn)
echo "🔄 Перезапускаю ProPart (Gunicorn)..."
sudo systemctl restart propart
sleep 5
PROPART_STATUS=$(sudo systemctl is-active propart)
if [ "$PROPART_STATUS" = "active" ]; then
    echo "✅ ProPart запущено"
else
    echo "❌ ProPart не запустився: $PROPART_STATUS"
    echo ""
    echo "📋 Останні логи помилок:"
    sudo journalctl -u propart -n 20 --no-pager
fi
echo ""

# 4. Перезапуск Nginx
echo "🔄 Перезапускаю Nginx..."
sudo systemctl restart nginx
sleep 2
NGINX_STATUS=$(sudo systemctl is-active nginx)
if [ "$NGINX_STATUS" = "active" ]; then
    echo "✅ Nginx запущено"
else
    echo "❌ Nginx не запустився: $NGINX_STATUS"
fi
echo ""

# 5. Підсумок
echo "=========================================="
echo "📊 СТАТУС СЕРВІСІВ:"
echo "=========================================="
echo ""

echo "🐘 PostgreSQL: $(sudo systemctl is-active postgresql)"
echo "🦄 ProPart:    $(sudo systemctl is-active propart)"
echo "🌐 Nginx:      $(sudo systemctl is-active nginx)"
echo ""

echo "🔌 Порт 8000: "
sudo netstat -tlnp | grep :8000 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Порт відкритий та слухається"
    sudo netstat -tlnp | grep :8000
else
    echo "❌ Нічого не слухає на порту 8000"
fi
echo ""

echo "=========================================="
echo "🌐 ТЕСТ ВЕБ-СЕРВЕРА:"
echo "=========================================="
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null)
echo "HTTP Status Code: $HTTP_STATUS"
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
    echo "✅ Веб-сервер відповідає"
else
    echo "❌ Веб-сервер не відповідає або помилка"
fi
echo ""

echo "=========================================="
echo "✅ ПЕРЕЗАПУСК ЗАВЕРШЕНО"
echo ""
echo "📌 Тепер спробуйте відкрити сайт у браузері:"
echo "   https://agent.pro-part.online"
echo ""

