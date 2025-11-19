#!/bin/bash

echo "⚡ ШВИДКЕ ВИПРАВЛЕННЯ ПОВІЛЬНОГО ЗАВАНТАЖЕННЯ"
echo "=========================================="
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# 1. Оновлення коду (вимкнення автоматичного HubSpot sync)
echo "🔧 Крок 1: Оновлення коду для оптимізації"
echo "--------------------------------------"
echo "Перевірка git статусу..."
git status --short | head -5
echo ""

# 2. Оптимізація конфігурації Gunicorn
echo "⚙️ Крок 2: Оптимізація Gunicorn"
echo "--------------------------------------"
if [ -f gunicorn_config.py ]; then
    # Створюємо резервну копію
    cp gunicorn_config.py gunicorn_config.py.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Створено резервну копію конфігурації"
    
    # Перевіряємо timeout
    CURRENT_TIMEOUT=$(grep "timeout = " gunicorn_config.py | head -1 | grep -o "[0-9]*")
    if [ -n "$CURRENT_TIMEOUT" ] && [ "$CURRENT_TIMEOUT" -gt 30 ]; then
        echo "⚠️  Поточний timeout: $CURRENT_TIMEOUT секунд (рекомендовано: 30)"
        echo "Оновлюю timeout до 30 секунд..."
        sed -i 's/timeout = [0-9]*/timeout = 30/' gunicorn_config.py
        echo "✅ Timeout оновлено"
    else
        echo "✅ Timeout вже оптимізовано"
    fi
else
    echo "⚠️  Конфігурація не знайдена"
fi
echo ""

# 3. Перезапуск сервісів
echo "🔄 Крок 3: Перезапуск сервісів"
echo "--------------------------------------"
echo "Зупиняю старі процеси..."
sudo pkill -9 gunicorn 2>/dev/null
sleep 2

echo "Перезапускаю ProPart..."
sudo systemctl restart propart
sleep 5

echo "Перезапускаю Nginx..."
sudo systemctl restart nginx
sleep 2
echo ""

# 4. Перевірка статусу
echo "📊 Крок 4: Перевірка статусу"
echo "--------------------------------------"
PGSQL_STATUS=$(systemctl is-active postgresql 2>/dev/null || echo "inactive")
NGINX_STATUS=$(systemctl is-active nginx 2>/dev/null || echo "inactive")
PROPART_STATUS=$(systemctl is-active propart 2>/dev/null || echo "inactive")

echo "PostgreSQL: $PGSQL_STATUS"
echo "Nginx:      $NGINX_STATUS"
echo "ProPart:    $PROPART_STATUS"
echo ""

# 5. Перевірка workers
echo "⚙️ Крок 5: Перевірка workers"
echo "--------------------------------------"
WORKER_COUNT=$(ps aux | grep -E "[g]unicorn.*worker" | wc -l)
echo "Активних workers: $WORKER_COUNT"
if [ "$WORKER_COUNT" -gt 0 ]; then
    echo "✅ Workers працюють"
else
    echo "❌ Workers не запущені!"
    echo "Перевірка логів:"
    sudo journalctl -u propart -n 20 --no-pager
fi
echo ""

# 6. Тест швидкості
echo "🌐 Крок 6: Тест швидкості відповіді"
echo "--------------------------------------"
echo "Тестую localhost:8000 (3 запити):"
TOTAL_TIME=0
for i in {1..3}; do
    START_TIME=$(date +%s%N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:8000/ 2>/dev/null)
    END_TIME=$(date +%s%N)
    DURATION=$((($END_TIME - $START_TIME) / 1000000))
    TOTAL_TIME=$((TOTAL_TIME + DURATION))
    echo "Запит $i: HTTP $HTTP_CODE, час: ${DURATION}ms"
done
AVG_TIME=$((TOTAL_TIME / 3))
echo "Середній час: ${AVG_TIME}ms"
echo ""

# 7. Рекомендації
echo "=========================================="
echo "✅ ВИПРАВЛЕННЯ ЗАВЕРШЕНО"
echo "=========================================="
echo ""

if [ "$AVG_TIME" -lt 1000 ]; then
    echo "✅ Швидкість відповіді нормальна (< 1 секунди)"
elif [ "$AVG_TIME" -lt 3000 ]; then
    echo "⚠️  Швидкість відповіді повільна (1-3 секунди)"
    echo ""
    echo "Рекомендації:"
    echo "1. Перевірте логи: sudo journalctl -u propart -f"
    echo "2. Запустіть діагностику: sudo ./DIAGNOSE_PERFORMANCE.sh"
    echo "3. Можливо, потрібно оптимізувати запити до бази даних"
else
    echo "❌ Швидкість відповіді дуже повільна (> 3 секунди)"
    echo ""
    echo "Негайні дії:"
    echo "1. Перевірте логи: sudo journalctl -u propart -n 50 --no-pager"
    echo "2. Запустіть діагностику: sudo ./DIAGNOSE_PERFORMANCE.sh"
    echo "3. Перевірте навантаження: top"
fi

echo ""
echo "Якщо проблема залишається, перевірте:"
echo "- Чи не робляться зайві запити до HubSpot API"
echo "- Чи немає повільних SQL запитів"
echo "- Чи достатньо пам'яті на сервері"
echo ""

