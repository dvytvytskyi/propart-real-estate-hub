#!/bin/bash

echo "🔍 ДІАГНОСТИКА ПРОДУКТИВНОСТІ"
echo "=========================================="
echo ""

# 1. Перевірка навантаження на CPU та пам'ять
echo "📊 КРОК 1: Навантаження на систему"
echo "--------------------------------------"
echo "CPU використання:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
echo ""
echo "Пам'ять:"
free -h
echo ""
echo "Навантаження:"
uptime
echo ""

# 2. Перевірка процесів Gunicorn
echo "⚙️ КРОК 2: Процеси Gunicorn"
echo "--------------------------------------"
GUNICORN_COUNT=$(ps aux | grep -E "[g]unicorn" | wc -l)
echo "Кількість workers: $GUNICORN_COUNT"
ps aux | grep -E "[g]unicorn" | head -10
echo ""

# 3. Перевірка використання пам'яті процесами
echo "💾 КРОК 3: Використання пам'яті"
echo "--------------------------------------"
ps aux --sort=-%mem | grep -E "[g]unicorn|propart" | head -5
echo ""

# 4. Перевірка логів на повільні запити
echo "⏱️ КРОК 4: Повільні запити (останні 20)"
echo "--------------------------------------"
if [ -f /var/log/propart/gunicorn_access.log ]; then
    echo "Аналіз логів доступу (запити довші за 1 секунду):"
    tail -100 /var/log/propart/gunicorn_access.log | awk '$NF > 1000000 {print}' | tail -20
else
    echo "Лог-файл не знайдено"
fi
echo ""

# 5. Перевірка підключень до бази даних
echo "🗄️ КРОК 5: Підключення до БД"
echo "--------------------------------------"
if command -v psql >/dev/null 2>&1; then
    echo "Активні підключення:"
    sudo -u postgres psql -d real_estate_agents -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'real_estate_agents';" 2>/dev/null || echo "Не вдалося перевірити"
    
    echo ""
    echo "Повільні запити (якщо є):"
    sudo -u postgres psql -d real_estate_agents -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds' AND state = 'active';" 2>/dev/null || echo "Немає повільних запитів"
else
    echo "PostgreSQL не встановлений або недоступний"
fi
echo ""

# 6. Перевірка конфігурації Gunicorn
echo "⚙️ КРОК 6: Конфігурація Gunicorn"
echo "--------------------------------------"
if [ -f /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/gunicorn_config.py ]; then
    echo "Workers:"
    grep "workers = " /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/gunicorn_config.py
    echo "Timeout:"
    grep "timeout = " /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/gunicorn_config.py
    echo "Worker class:"
    grep "worker_class = " /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/gunicorn_config.py
else
    echo "Конфігурація не знайдена"
fi
echo ""

# 7. Тест швидкості відповіді
echo "🌐 КРОК 7: Тест швидкості відповіді"
echo "--------------------------------------"
echo "Тестую localhost:8000 (3 запити):"
for i in {1..3}; do
    START_TIME=$(date +%s%N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:8000/ 2>/dev/null)
    END_TIME=$(date +%s%N)
    DURATION=$((($END_TIME - $START_TIME) / 1000000))
    echo "Запит $i: HTTP $HTTP_CODE, час: ${DURATION}ms"
done
echo ""

# 8. Перевірка помилок
echo "📋 КРОК 8: Останні помилки"
echo "--------------------------------------"
if [ -f /var/log/propart/gunicorn_error.log ]; then
    echo "Останні помилки:"
    tail -20 /var/log/propart/gunicorn_error.log | grep -i "error\|timeout\|slow" || echo "Помилок не знайдено"
else
    echo "Лог-файл не знайдено"
fi
echo ""

echo "=========================================="
echo "✅ ДІАГНОСТИКА ЗАВЕРШЕНА"
echo ""
echo "Рекомендації:"
echo "1. Якщо workers занадто багато - зменшити кількість"
echo "2. Якщо є повільні запити - перевірити базу даних"
echo "3. Якщо високе використання пам'яті - перезапустити сервіс"
echo ""

