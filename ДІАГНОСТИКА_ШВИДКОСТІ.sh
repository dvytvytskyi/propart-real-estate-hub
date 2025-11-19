#!/bin/bash

echo "🔍 ДІАГНОСТИКА ШВИДКОСТІ ЗАВАНТАЖЕННЯ"
echo "=========================================="
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# 1. Перевірка чи вимкнено автоматичну синхронізацію
echo "📊 КРОК 1: Перевірка автоматичної синхронізації"
echo "--------------------------------------"
if grep -q "# ⚡ ВИМКНЕНО: start_background_sync" app.py; then
    echo "✅ Автоматична синхронізація ВИМКНЕНА"
else
    echo "❌ Автоматична синхронізація АКТИВНА (це може сповільнювати)"
    echo "   Рекомендація: вимкнути через ./ПОВНЕ_ВИМКНЕННЯ_HUBSPOT.sh"
fi
echo ""

# 2. Перевірка чи є активні виклики HubSpot в dashboard
echo "📊 КРОК 2: Перевірка викликів HubSpot в dashboard"
echo "--------------------------------------"
if grep -A 5 "@app.route('/dashboard')" app.py | grep -E "hubspot_client|sync_all|update_hubspot" | grep -v "^[[:space:]]*#"; then
    echo "⚠️  Знайдено активні виклики HubSpot в dashboard"
else
    echo "✅ Dashboard не робить автоматичних викликів HubSpot"
fi
echo ""

# 3. Перевірка навантаження на систему
echo "📊 КРОК 3: Навантаження на систему"
echo "--------------------------------------"
echo "CPU використання:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
echo ""
echo "Пам'ять:"
free -h | grep Mem
echo ""
echo "Навантаження:"
uptime
echo ""

# 4. Перевірка процесів Gunicorn
echo "📊 КРОК 4: Процеси Gunicorn"
echo "--------------------------------------"
GUNICORN_COUNT=$(ps aux | grep -E "[g]unicorn.*worker" | wc -l)
echo "Кількість workers: $GUNICORN_COUNT"
if [ "$GUNICORN_COUNT" -gt 0 ]; then
    echo "Використання пам'яті workers:"
    ps aux | grep -E "[g]unicorn.*worker" | awk '{sum+=$6} END {print "Загалом: " sum/1024 " MB"}'
fi
echo ""

# 5. Тест швидкості відповіді
echo "📊 КРОК 5: Тест швидкості відповіді (5 запитів)"
echo "--------------------------------------"
TOTAL_TIME=0
SUCCESS_COUNT=0
for i in {1..5}; do
    START=$(date +%s%N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:8000/ 2>/dev/null)
    END=$(date +%s%N)
    TIME=$((($END - $START) / 1000000))
    TOTAL_TIME=$((TOTAL_TIME + TIME))
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    fi
    echo "Запит $i: HTTP $HTTP_CODE, час: ${TIME}ms"
done
AVG_TIME=$((TOTAL_TIME / 5))
echo ""
echo "Середній час: ${AVG_TIME}ms"
echo "Успішних запитів: $SUCCESS_COUNT/5"
echo ""

# 6. Перевірка логів на повільні запити
echo "📊 КРОК 6: Повільні запити в логах"
echo "--------------------------------------"
if [ -f /var/log/propart/gunicorn_access.log ]; then
    echo "Останні запити довші за 1 секунду:"
    tail -100 /var/log/propart/gunicorn_access.log | awk '$NF > 1000000 {print}' | tail -5 || echo "Повільних запитів не знайдено"
else
    echo "Лог-файл не знайдено"
fi
echo ""

# 7. Перевірка підключень до бази даних
echo "📊 КРОК 7: Підключення до БД"
echo "--------------------------------------"
if command -v psql >/dev/null 2>&1; then
    ACTIVE_CONNECTIONS=$(sudo -u postgres psql -d real_estate_agents -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'real_estate_agents';" 2>/dev/null | tr -d ' ')
    echo "Активних підключень: $ACTIVE_CONNECTIONS"
    
    SLOW_QUERIES=$(sudo -u postgres psql -d real_estate_agents -t -c "SELECT count(*) FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '1 second' AND state = 'active';" 2>/dev/null | tr -d ' ')
    if [ -n "$SLOW_QUERIES" ] && [ "$SLOW_QUERIES" -gt 0 ]; then
        echo "⚠️  Знайдено повільних запитів: $SLOW_QUERIES"
    else
        echo "✅ Повільних запитів не знайдено"
    fi
else
    echo "PostgreSQL не доступний для перевірки"
fi
echo ""

# 8. Підсумок та рекомендації
echo "=========================================="
echo "📊 ПІДСУМОК"
echo "=========================================="
echo ""

if [ "$AVG_TIME" -lt 500 ]; then
    echo "✅ Швидкість відповіді відмінна (< 500ms)"
elif [ "$AVG_TIME" -lt 1000 ]; then
    echo "⚠️  Швидкість відповіді нормальна (500ms - 1s)"
elif [ "$AVG_TIME" -lt 3000 ]; then
    echo "❌ Швидкість відповіді повільна (1s - 3s)"
    echo ""
    echo "Рекомендації:"
    echo "1. Вимкнути автоматичну синхронізацію: sudo ./ПОВНЕ_ВИМКНЕННЯ_HUBSPOT.sh"
    echo "2. Перевірити логи: sudo journalctl -u propart -f"
    echo "3. Перевірити навантаження на БД"
else
    echo "🚨 Швидкість відповіді ДУЖЕ повільна (> 3s)"
    echo ""
    echo "НЕГАЙНІ ДІЇ:"
    echo "1. Вимкнути автоматичну синхронізацію: sudo ./ПОВНЕ_ВИМКНЕННЯ_HUBSPOT.sh"
    echo "2. Перезапустити сервіси: sudo systemctl restart propart nginx"
    echo "3. Перевірити логи: sudo journalctl -u propart -n 50 --no-pager"
fi

echo ""

