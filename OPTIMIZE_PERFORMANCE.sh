#!/bin/bash

echo "⚡ ОПТИМІЗАЦІЯ ПРОДУКТИВНОСТІ"
echo "=========================================="
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# 1. Перевірка поточної конфігурації
echo "📊 Крок 1: Поточна конфігурація Gunicorn"
echo "--------------------------------------"
if [ -f gunicorn_config.py ]; then
    echo "Workers:"
    grep "workers = " gunicorn_config.py
    echo "Timeout:"
    grep "timeout = " gunicorn_config.py | head -1
else
    echo "❌ Конфігурація не знайдена"
fi
echo ""

# 2. Оптимізація конфігурації Gunicorn
echo "🔧 Крок 2: Оптимізація конфігурації Gunicorn"
echo "--------------------------------------"

# Створюємо резервну копію
if [ -f gunicorn_config.py ]; then
    cp gunicorn_config.py gunicorn_config.py.backup
    echo "✅ Створено резервну копію: gunicorn_config.py.backup"
fi

# Оновлюємо конфігурацію
cat > /tmp/gunicorn_optimized.py << 'GUNICORN_EOF'
"""
Gunicorn конфігурація для ProPart Real Estate Hub
Оптимізована для продуктивності
"""
import multiprocessing
import os

# Server Socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker Processes - оптимізовано
cpu_count = multiprocessing.cpu_count()
if cpu_count <= 2:
    workers = 3  # Мінімум 3 workers для стабільності
elif cpu_count <= 4:
    workers = cpu_count + 1  # Для 4 CPU: 5 workers
else:
    workers = cpu_count * 2 + 1  # Для більших серверів: стандартна формула

worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30  # Зменшено для швидшого виявлення проблем
graceful_timeout = 15
keepalive = 2

# Logging
accesslog = "/var/log/propart/gunicorn_access.log"
errorlog = "/var/log/propart/gunicorn_error.log"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "propart_hub"

# Server Mechanics
daemon = False
pidfile = "/var/run/propart/gunicorn.pid"
umask = 0
user = "www-data"
group = "www-data"

# Preload app for better memory usage
preload_app = True

# Environment
raw_env = [
    'FLASK_ENV=production',
]
GUNICORN_EOF

mv /tmp/gunicorn_optimized.py gunicorn_config.py
echo "✅ Конфігурація оновлена"
echo ""

# 3. Перезапуск сервісу
echo "🔄 Крок 3: Перезапуск ProPart"
echo "--------------------------------------"
sudo systemctl restart propart
sleep 5

# 4. Перевірка статусу
echo "📊 Крок 4: Перевірка статусу"
echo "--------------------------------------"
PROPART_STATUS=$(systemctl is-active propart 2>/dev/null || echo "inactive")
if [ "$PROPART_STATUS" = "active" ]; then
    echo "✅ ProPart працює"
else
    echo "❌ ProPart не працює"
    echo "Перевірка логів:"
    sudo journalctl -u propart -n 20 --no-pager
fi
echo ""

# 5. Перевірка кількості workers
echo "⚙️ Крок 5: Перевірка workers"
echo "--------------------------------------"
WORKER_COUNT=$(ps aux | grep -E "[g]unicorn.*worker" | wc -l)
echo "Активних workers: $WORKER_COUNT"
ps aux | grep -E "[g]unicorn.*worker" | head -5
echo ""

# 6. Тест швидкості
echo "🌐 Крок 6: Тест швидкості відповіді"
echo "--------------------------------------"
for i in {1..3}; do
    START_TIME=$(date +%s%N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://localhost:8000/ 2>/dev/null)
    END_TIME=$(date +%s%N)
    DURATION=$((($END_TIME - $START_TIME) / 1000000))
    echo "Запит $i: HTTP $HTTP_CODE, час: ${DURATION}ms"
done
echo ""

echo "=========================================="
echo "✅ ОПТИМІЗАЦІЯ ЗАВЕРШЕНА"
echo ""
echo "Рекомендації:"
echo "1. Якщо все ще повільно - перевірте логи: sudo journalctl -u propart -f"
echo "2. Перевірте навантаження: sudo ./DIAGNOSE_PERFORMANCE.sh"
echo "3. Можливо, потрібно оптимізувати запити до HubSpot API"
echo ""

