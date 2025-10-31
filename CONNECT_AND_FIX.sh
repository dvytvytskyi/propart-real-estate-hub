#!/bin/bash

# Скрипт для підключення до сервера та виправлення помилки 502

SERVER_IP="188.245.228.175"
SERVER_USER="root"
SERVER_PASSWORD="7NdMqCMV4wtw"

echo "🔐 Підключення до сервера $SERVER_IP..."
echo ""

# Створюємо тимчасовий скрипт для виконання на сервері
cat > /tmp/fix_server.sh << 'EOFSCRIPT'
#!/bin/bash

echo "🔧 ВИПРАВЛЕННЯ ПОМИЛКИ 502 НА СЕРВЕРІ"
echo "=========================================="
echo ""

# Перехід в директорію проекту
cd /var/www/propart 2>/dev/null || cd /root/propart-real-estate-hub 2>/dev/null || {
    echo "❌ Проект не знайдено!"
    echo "Шукаю в інших місцях..."
    find / -name "app.py" -path "*/propart*" 2>/dev/null | head -1
    exit 1
}

echo "📁 Поточна директорія: $(pwd)"
echo ""

# Оновлення коду
echo "📥 Оновлення коду..."
git stash 2>/dev/null
git pull origin main 2>/dev/null || git pull 2>/dev/null || echo "⚠️ Git pull пропущено"
echo ""

# Зупинка Gunicorn
echo "🛑 Зупинка Gunicorn..."
pkill -9 gunicorn 2>/dev/null
sleep 2
echo "✅ Gunicorn зупинено"
echo ""

# Перезапуск PostgreSQL
echo "🔄 Перезапуск PostgreSQL..."
systemctl restart postgresql
sleep 3
echo "PostgreSQL: $(systemctl is-active postgresql)"
echo ""

# Перезапуск ProPart
echo "🔄 Перезапуск ProPart..."
systemctl restart propart
sleep 5
echo "ProPart: $(systemctl is-active propart)"
echo ""

# Перезапуск Nginx
echo "🔄 Перезапуск Nginx..."
systemctl restart nginx
sleep 2
echo "Nginx: $(systemctl is-active nginx)"
echo ""

# Перевірка статусу
echo "=========================================="
echo "📊 ПІДСУМОК:"
echo "=========================================="
echo ""
echo "🐘 PostgreSQL: $(systemctl is-active postgresql)"
echo "🦄 ProPart:    $(systemctl is-active propart)"
echo "🌐 Nginx:      $(systemctl is-active nginx)"
echo ""

# Перевірка процесів
GUNICORN_COUNT=$(ps aux | grep gunicorn | grep -v grep | wc -l)
echo "⚙️ Gunicorn процесів: $GUNICORN_COUNT"
echo ""

# Перевірка порту
echo "🔌 Порт 8000:"
netstat -tlnp | grep :8000 || echo "❌ Порт не слухається"
echo ""

# Тест HTTP
echo "🌐 Тест HTTP:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null)
echo "HTTP Code: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo "=========================================="
    echo "✅ ВСЕ ПРАЦЮЄ!"
    echo "=========================================="
    echo ""
    echo "🎉 Відкрийте в браузері:"
    echo "   https://agent.pro-part.online"
    echo ""
else
    echo "=========================================="
    echo "⚠️ Є ПРОБЛЕМИ"
    echo "=========================================="
    echo ""
    echo "📋 Останні логи ProPart:"
    journalctl -u propart -n 20 --no-pager
    echo ""
    echo "📋 Gunicorn error log:"
    tail -20 /var/log/propart/gunicorn_error.log 2>/dev/null || echo "Лог не знайдено"
fi

EOFSCRIPT

# Підключення до сервера та виконання скрипту
echo "Підключаюсь до сервера..."
echo ""

# Використовуємо sshpass якщо доступний, інакше інтерактивне підключення
if command -v sshpass &> /dev/null; then
    echo "✅ Використовую sshpass для автоматичного підключення"
    sshpass -p "$SERVER_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $SERVER_USER@$SERVER_IP 'bash -s' < /tmp/fix_server.sh
else
    echo "⚠️ sshpass не знайдено, використовую стандартне SSH підключення"
    echo "Введіть пароль коли буде запитано: $SERVER_PASSWORD"
    echo ""
    ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP 'bash -s' < /tmp/fix_server.sh
fi

# Очищення
rm -f /tmp/fix_server.sh

echo ""
echo "=========================================="
echo "✅ ГОТОВО!"
echo "=========================================="

