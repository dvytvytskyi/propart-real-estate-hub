#!/bin/bash

echo "⚡ ШВИДКЕ ВИПРАВЛЕННЯ ПОМИЛКИ 502"
echo "=========================================="
echo ""

# Кольори
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Функція для перевірки та виведення статусу
check_and_restart() {
    SERVICE=$1
    NAME=$2
    
    STATUS=$(systemctl is-active $SERVICE 2>/dev/null || echo "inactive")
    if [ "$STATUS" != "active" ]; then
        echo -e "${YELLOW}⚠️  $NAME не працює, запускаю...${NC}"
        sudo systemctl start $SERVICE
        sleep 2
        NEW_STATUS=$(systemctl is-active $SERVICE 2>/dev/null || echo "inactive")
        if [ "$NEW_STATUS" = "active" ]; then
            echo -e "${GREEN}✅ $NAME запущено${NC}"
        else
            echo -e "${RED}❌ Не вдалося запустити $NAME${NC}"
            return 1
        fi
    else
        echo -e "${GREEN}✅ $NAME працює${NC}"
    fi
    return 0
}

# 1. Зупинка всіх старих процесів Gunicorn
echo "🛑 Крок 1: Очищення старих процесів"
echo "--------------------------------------"
sudo pkill -9 gunicorn 2>/dev/null
sleep 2
echo "✅ Готово"
echo ""

# 2. Перезапуск PostgreSQL
echo "🔄 Крок 2: Перезапуск PostgreSQL"
echo "--------------------------------------"
check_and_restart "postgresql" "PostgreSQL"
echo ""

# 3. Перезапуск ProPart
echo "🔄 Крок 3: Перезапуск ProPart (Gunicorn)"
echo "--------------------------------------"
# Спочатку зупинити
sudo systemctl stop propart 2>/dev/null
sleep 2
# Потім запустити
check_and_restart "propart" "ProPart"
echo ""

# 4. Перезапуск Nginx
echo "🔄 Крок 4: Перезапуск Nginx"
echo "--------------------------------------"
check_and_restart "nginx" "Nginx"
echo ""

# 5. Перевірка порту 8000
echo "🔌 Крок 5: Перевірка порту 8000"
echo "--------------------------------------"
sleep 3
if command -v netstat >/dev/null 2>&1; then
    PORT_CHECK=$(sudo netstat -tlnp | grep :8000)
elif command -v ss >/dev/null 2>&1; then
    PORT_CHECK=$(sudo ss -tlnp | grep :8000)
else
    PORT_CHECK=$(sudo lsof -i :8000 2>/dev/null)
fi

if [ -n "$PORT_CHECK" ]; then
    echo -e "${GREEN}✅ Порт 8000 відкритий${NC}"
    echo "$PORT_CHECK"
else
    echo -e "${RED}❌ Порт 8000 не відкритий!${NC}"
    echo ""
    echo "Перевірка логів ProPart:"
    sudo journalctl -u propart -n 20 --no-pager
fi
echo ""

# 6. Тест HTTP
echo "🌐 Крок 6: Тест HTTP запиту"
echo "--------------------------------------"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8000/ 2>/dev/null)
if [ -n "$HTTP_STATUS" ]; then
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
        echo -e "${GREEN}✅ Gunicorn відповідає (HTTP $HTTP_STATUS)${NC}"
    else
        echo -e "${YELLOW}⚠️  Gunicorn відповідає з кодом HTTP $HTTP_STATUS${NC}"
    fi
else
    echo -e "${RED}❌ Gunicorn не відповідає${NC}"
fi
echo ""

# 7. Підсумок
echo "=========================================="
echo "📊 ПІДСУМОК"
echo "=========================================="
echo ""

PGSQL_FINAL=$(systemctl is-active postgresql 2>/dev/null || echo "inactive")
NGINX_FINAL=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
PROPART_FINAL=$(systemctl is-active propart 2>/dev/null || echo "inactive")

echo "PostgreSQL: $PGSQL_FINAL"
echo "Nginx:      $NGINX_FINAL"
echo "ProPart:    $PROPART_FINAL"
echo ""

if [ "$PGSQL_FINAL" = "active" ] && [ "$NGINX_FINAL" = "active" ] && [ "$PROPART_FINAL" = "active" ]; then
    echo -e "${GREEN}✅ Всі сервіси працюють!${NC}"
    echo ""
    echo "Спробуйте відкрити сайт у браузері:"
    echo "   https://agent.pro-part.online"
else
    echo -e "${YELLOW}⚠️  Деякі сервіси не працюють${NC}"
    echo ""
    echo "Для детальної діагностики виконайте:"
    echo "   sudo ./DIAGNOSE_502.sh"
fi

echo ""
echo "=========================================="

