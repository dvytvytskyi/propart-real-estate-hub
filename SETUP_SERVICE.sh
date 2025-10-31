#!/bin/bash

echo "🔧 НАЛАШТУВАННЯ СЕРВІСУ PROPART"
echo "=========================================="
echo ""

# 1. Створення необхідних директорій
echo "📁 Створення директорій..."
mkdir -p /var/run/propart
mkdir -p /var/log/propart
chown -R www-data:www-data /var/run/propart
chown -R www-data:www-data /var/log/propart
echo "✅ Директорії створено"
echo ""

# 2. Створення systemd unit file
echo "📝 Створення systemd unit file..."
cat > /etc/systemd/system/propart.service << 'EOF'
[Unit]
Description=ProPart Real Estate Hub - Gunicorn Application Server
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=propart
WorkingDirectory=/var/www/propart
Environment="PATH=/var/www/propart/venv/bin"
ExecStart=/var/www/propart/venv/bin/gunicorn --config /var/www/propart/gunicorn_config.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
echo "✅ Unit file створено"
echo ""

# 3. Оновлення конфігурації Gunicorn (видалити user/group якщо запускається через systemd)
echo "📝 Оновлення gunicorn_config.py..."
cd /var/www/propart

# Створюємо бекап
cp gunicorn_config.py gunicorn_config.py.bak

# Оновлюємо конфіг
cat > gunicorn_config.py << 'EOF'
"""
Gunicorn конфігурація для ProPart Real Estate Hub
Production-ready configuration
"""
import multiprocessing
import os

# Server Socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 60
graceful_timeout = 30
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
# НЕ вказуємо user/group тут - systemd керує цим
# НЕ вказуємо pidfile - systemd керує цим

# Preload app for better memory usage
preload_app = True

# Environment
raw_env = [
    'FLASK_ENV=production',
]
EOF
echo "✅ Конфігурація оновлена"
echo ""

# 4. Перезавантаження systemd
echo "🔄 Перезавантаження systemd..."
systemctl daemon-reload
echo "✅ Systemd перезавантажено"
echo ""

# 5. Увімкнення автозапуску
echo "🚀 Увімкнення автозапуску..."
systemctl enable propart
echo "✅ Автозапуск увімкнено"
echo ""

# 6. Запуск сервісу
echo "🔄 Запуск ProPart..."
systemctl start propart
sleep 5
echo ""

# 7. Перевірка статусу
echo "=========================================="
echo "📊 СТАТУС СЕРВІСУ:"
echo "=========================================="
echo ""
systemctl status propart --no-pager -l
echo ""

# 8. Перевірка процесів
echo "⚙️ Процеси Gunicorn:"
ps aux | grep gunicorn | grep -v grep
echo ""

# 9. Перевірка порту
echo "🔌 Порт 8000:"
netstat -tlnp | grep :8000
echo ""

# 10. Тест HTTP
echo "🌐 Тест HTTP:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null)
echo "HTTP Code: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo "=========================================="
    echo "✅ ВСЕ ПРАЦЮЄ!"
    echo "=========================================="
    echo ""
    echo "🎉 Сервіс налаштовано і запущено!"
    echo ""
    echo "📌 Відкрийте в браузері:"
    echo "   https://agent.pro-part.online"
    echo ""
else
    echo "=========================================="
    echo "⚠️ Є ПРОБЛЕМИ"
    echo "=========================================="
    echo ""
    echo "📋 Логи для діагностики:"
    journalctl -u propart -n 30 --no-pager
    echo ""
    echo "📋 Gunicorn error log:"
    tail -20 /var/log/propart/gunicorn_error.log
fi

