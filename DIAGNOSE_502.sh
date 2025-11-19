#!/bin/bash

echo "🔍 ДІАГНОСТИКА ПОМИЛКИ 502 BAD GATEWAY"
echo "=========================================="
echo ""

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функція для виводу статусу
print_status() {
    if [ "$1" = "active" ] || [ "$1" = "running" ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# 1. Перевірка статусу сервісів
echo "📊 КРОК 1: Статус сервісів"
echo "--------------------------------------"

PGSQL_STATUS=$(systemctl is-active postgresql 2>/dev/null || echo "inactive")
print_status "$PGSQL_STATUS" "PostgreSQL: $PGSQL_STATUS"

NGINX_STATUS=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
print_status "$NGINX_STATUS" "Nginx: $NGINX_STATUS"

PROPART_STATUS=$(systemctl is-active propart 2>/dev/null || echo "inactive")
print_status "$PROPART_STATUS" "ProPart (Gunicorn): $PROPART_STATUS"

echo ""

# 2. Перевірка порту 8000
echo "🔌 КРОК 2: Перевірка порту 8000"
echo "--------------------------------------"
PORT_CHECK=$(netstat -tlnp 2>/dev/null | grep :8000 || ss -tlnp 2>/dev/null | grep :8000 || echo "")
if [ -n "$PORT_CHECK" ]; then
    echo -e "${GREEN}✅ Порт 8000 відкритий:${NC}"
    echo "$PORT_CHECK"
else
    echo -e "${RED}❌ Порт 8000 НЕ відкритий - Gunicorn не слухає!${NC}"
fi
echo ""

# 3. Перевірка процесів Gunicorn
echo "⚙️ КРОК 3: Процеси Gunicorn"
echo "--------------------------------------"
GUNICORN_PROCS=$(ps aux | grep -E "[g]unicorn|propart" | wc -l)
if [ "$GUNICORN_PROCS" -gt 0 ]; then
    echo -e "${GREEN}✅ Знайдено процесів: $GUNICORN_PROCS${NC}"
    ps aux | grep -E "[g]unicorn|propart" | head -5
else
    echo -e "${RED}❌ Процеси Gunicorn не знайдені!${NC}"
fi
echo ""

# 4. Перевірка конфігурації Nginx
echo "🔍 КРОК 4: Конфігурація Nginx"
echo "--------------------------------------"
if command -v nginx >/dev/null 2>&1; then
    NGINX_TEST=$(nginx -t 2>&1)
    if echo "$NGINX_TEST" | grep -q "successful"; then
        echo -e "${GREEN}✅ Конфігурація Nginx валідна${NC}"
    else
        echo -e "${RED}❌ Помилка в конфігурації Nginx:${NC}"
        echo "$NGINX_TEST"
    fi
else
    echo -e "${YELLOW}⚠️  Nginx не встановлений${NC}"
fi
echo ""

# 5. Перевірка підключення до бази даних
echo "🗄️ КРОК 5: Підключення до бази даних"
echo "--------------------------------------"
if command -v psql >/dev/null 2>&1; then
    DB_CHECK=$(sudo -u postgres psql -d real_estate_agents -c "SELECT 1;" 2>&1 | head -3)
    if echo "$DB_CHECK" | grep -q "1 row"; then
        echo -e "${GREEN}✅ Підключення до БД успішне${NC}"
    else
        echo -e "${YELLOW}⚠️  Проблема з підключенням до БД:${NC}"
        echo "$DB_CHECK" | head -5
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL не встановлений${NC}"
fi
echo ""

# 6. Перевірка логів Gunicorn
echo "📋 КРОК 6: Останні помилки Gunicorn"
echo "--------------------------------------"
LOG_FILES=(
    "/var/log/propart/gunicorn_error.log"
    "/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/logs/propart.log"
    "/var/log/gunicorn/error.log"
)

FOUND_LOG=false
for LOG_FILE in "${LOG_FILES[@]}"; do
    if [ -f "$LOG_FILE" ]; then
        echo -e "${GREEN}📄 Лог: $LOG_FILE${NC}"
        tail -15 "$LOG_FILE"
        FOUND_LOG=true
        echo ""
        break
    fi
done

if [ "$FOUND_LOG" = false ]; then
    echo "Перевірка systemd журналу..."
    journalctl -u propart -n 20 --no-pager 2>/dev/null || echo "Логи не знайдені"
fi
echo ""

# 7. Перевірка логів Nginx
echo "📋 КРОK 7: Останні помилки Nginx"
echo "--------------------------------------"
NGINX_ERROR_LOG="/var/log/nginx/propart_error.log"
if [ -f "$NGINX_ERROR_LOG" ]; then
    echo "Останні помилки Nginx:"
    tail -10 "$NGINX_ERROR_LOG"
else
    echo "Перевірка загального логу Nginx..."
    tail -10 /var/log/nginx/error.log 2>/dev/null || echo "Логи не знайдені"
fi
echo ""

# 8. Тест HTTP запиту
echo "🌐 КРОК 8: Тест HTTP запиту"
echo "--------------------------------------"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://localhost:8000/ 2>/dev/null)
if [ -n "$HTTP_STATUS" ]; then
    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "301" ]; then
        echo -e "${GREEN}✅ Gunicorn відповідає (HTTP $HTTP_STATUS)${NC}"
    else
        echo -e "${YELLOW}⚠️  Gunicorn відповідає з помилкою (HTTP $HTTP_STATUS)${NC}"
    fi
else
    echo -e "${RED}❌ Gunicorn не відповідає на запити${NC}"
fi
echo ""

# 9. Перевірка шляхів та прав доступу
echo "📁 КРОК 9: Перевірка шляхів"
echo "--------------------------------------"
WORK_DIR="/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub"
if [ -d "$WORK_DIR" ]; then
    echo -e "${GREEN}✅ Робоча директорія існує: $WORK_DIR${NC}"
    
    # Перевірка .env файлу
    if [ -f "$WORK_DIR/.env" ]; then
        echo -e "${GREEN}✅ .env файл існує${NC}"
    else
        echo -e "${RED}❌ .env файл НЕ знайдено!${NC}"
    fi
    
    # Перевірка venv
    if [ -d "$WORK_DIR/venv" ]; then
        echo -e "${GREEN}✅ venv існує${NC}"
    else
        echo -e "${RED}❌ venv НЕ знайдено!${NC}"
    fi
else
    echo -e "${RED}❌ Робоча директорія НЕ знайдена: $WORK_DIR${NC}"
fi
echo ""

# 10. ПІДСУМОК ТА РЕКОМЕНДАЦІЇ
echo "=========================================="
echo "📊 ПІДСУМОК"
echo "=========================================="
echo ""

ISSUES=0

if [ "$PGSQL_STATUS" != "active" ]; then
    echo -e "${RED}❌ PostgreSQL не працює${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$NGINX_STATUS" != "active" ]; then
    echo -e "${RED}❌ Nginx не працює${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$PROPART_STATUS" != "active" ]; then
    echo -e "${RED}❌ ProPart (Gunicorn) не працює${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ -z "$PORT_CHECK" ]; then
    echo -e "${RED}❌ Порт 8000 не відкритий${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$GUNICORN_PROCS" -eq 0 ]; then
    echo -e "${RED}❌ Процеси Gunicorn не запущені${NC}"
    ISSUES=$((ISSUES + 1))
fi

echo ""
if [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}✅ Всі перевірки пройдені успішно!${NC}"
    echo ""
    echo "Якщо досі є помилка 502, спробуйте:"
    echo "  1. Перезапустити всі сервіси: sudo ./RESTART_ALL_SERVICES.sh"
    echo "  2. Перевірити логи: sudo journalctl -u propart -f"
else
    echo -e "${YELLOW}⚠️  Знайдено $ISSUES проблем(и)${NC}"
    echo ""
    echo "Рекомендовані дії:"
    echo "  1. Запустити виправлення: sudo ./FIX_502_ERROR.sh"
    echo "  2. Або перезапустити сервіси: sudo ./RESTART_ALL_SERVICES.sh"
fi

echo ""
echo "=========================================="

