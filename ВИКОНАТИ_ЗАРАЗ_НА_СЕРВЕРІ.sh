#!/bin/bash
# ШВИДКЕ ВИПРАВЛЕННЯ 502 - ВИКОНАТИ НА СЕРВЕРІ

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

echo "⚡ ШВИДКЕ ВИПРАВЛЕННЯ ПОМИЛКИ 502"
echo "=========================================="
echo ""

# 1. Зупинити всі процеси Gunicorn
echo "🛑 Зупиняю старі процеси Gunicorn..."
sudo pkill -9 gunicorn 2>/dev/null
sleep 2

# 2. Перезапустити PostgreSQL
echo "🔄 Перезапускаю PostgreSQL..."
sudo systemctl restart postgresql
sleep 3

# 3. Перезапустити ProPart
echo "🔄 Перезапускаю ProPart (Gunicorn)..."
sudo systemctl restart propart
sleep 5

# 4. Перезапустити Nginx
echo "🔄 Перезапускаю Nginx..."
sudo systemctl restart nginx
sleep 2

# 5. Перевірка статусу
echo ""
echo "=========================================="
echo "📊 СТАТУС СЕРВІСІВ:"
echo "=========================================="
echo ""

PGSQL_STATUS=$(systemctl is-active postgresql 2>/dev/null || echo "inactive")
NGINX_STATUS=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
PROPART_STATUS=$(systemctl is-active propart 2>/dev/null || echo "inactive")

echo "PostgreSQL: $PGSQL_STATUS"
echo "Nginx:      $NGINX_STATUS"
echo "ProPart:    $PROPART_STATUS"
echo ""

# 6. Перевірка порту 8000
echo "🔌 Перевірка порту 8000:"
if command -v netstat >/dev/null 2>&1; then
    PORT_CHECK=$(sudo netstat -tlnp | grep :8000)
elif command -v ss >/dev/null 2>&1; then
    PORT_CHECK=$(sudo ss -tlnp | grep :8000)
fi

if [ -n "$PORT_CHECK" ]; then
    echo "✅ Порт 8000 відкритий"
    echo "$PORT_CHECK"
else
    echo "❌ Порт 8000 не відкритий!"
    echo ""
    echo "Перевірка логів:"
    sudo journalctl -u propart -n 20 --no-pager
fi
echo ""

# 7. Тест HTTP
echo "🌐 Тест HTTP запиту:"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8000/ 2>/dev/null)
if [ -n "$HTTP_STATUS" ]; then
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
        echo "✅ Gunicorn відповідає (HTTP $HTTP_STATUS)"
    else
        echo "⚠️  Gunicorn відповідає з кодом HTTP $HTTP_STATUS"
    fi
else
    echo "❌ Gunicorn не відповідає"
fi
echo ""

if [ "$PGSQL_STATUS" = "active" ] && [ "$NGINX_STATUS" = "active" ] && [ "$PROPART_STATUS" = "active" ]; then
    echo "✅ Всі сервіси працюють!"
    echo ""
    echo "Спробуйте відкрити сайт:"
    echo "   https://agent.pro-part.online"
else
    echo "⚠️  Деякі сервіси не працюють"
    echo ""
    echo "Для детальної діагностики:"
    echo "   sudo journalctl -u propart -n 50 --no-pager"
fi

echo ""
echo "=========================================="

