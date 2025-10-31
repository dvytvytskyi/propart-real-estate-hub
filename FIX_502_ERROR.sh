#!/bin/bash

echo "🔧 ДІАГНОСТИКА ТА ВИПРАВЛЕННЯ ПОМИЛКИ 502"
echo "=========================================="
echo ""

# 1. Перевірка статусу сервісів
echo "📊 Крок 1: Перевірка статусу сервісів"
echo "--------------------------------------"

echo "🐘 PostgreSQL:"
sudo systemctl status postgresql --no-pager | grep "Active:" || echo "❌ PostgreSQL недоступний"
echo ""

echo "🌐 Nginx:"
sudo systemctl status nginx --no-pager | grep "Active:" || echo "❌ Nginx недоступний"
echo ""

echo "🦄 Gunicorn (ProPart):"
sudo systemctl status propart --no-pager | grep "Active:" || echo "❌ Gunicorn не запущений"
echo ""

# 2. Перевірка логів Gunicorn
echo "📋 Крок 2: Перевірка логів Gunicorn (останні 20 рядків)"
echo "--------------------------------------"
if [ -f /var/log/propart/gunicorn_error.log ]; then
    tail -20 /var/log/propart/gunicorn_error.log
else
    echo "❌ Лог-файл не знайдено: /var/log/propart/gunicorn_error.log"
fi
echo ""

# 3. Перевірка конфігурації Nginx
echo "🔍 Крок 3: Перевірка конфігурації Nginx"
echo "--------------------------------------"
sudo nginx -t 2>&1
echo ""

# 4. Перевірка підключення до бази даних
echo "🗄️ Крок 4: Перевірка підключення до бази даних"
echo "--------------------------------------"
sudo -u postgres psql -d real_estate_agents -c "SELECT COUNT(*) FROM users;" 2>&1 | head -5 || echo "❌ Помилка підключення до бази даних"
echo ""

# 5. Перевірка процесів Gunicorn
echo "⚙️ Крок 5: Перевірка процесів Gunicorn"
echo "--------------------------------------"
GUNICORN_PROCESSES=$(ps aux | grep gunicorn | grep -v grep | wc -l)
echo "Знайдено процесів Gunicorn: $GUNICORN_PROCESSES"
if [ $GUNICORN_PROCESSES -eq 0 ]; then
    echo "❌ Gunicorn не запущений!"
else
    echo "✅ Gunicorn працює"
    ps aux | grep gunicorn | grep -v grep | head -3
fi
echo ""

# 6. Перевірка порту 8000 (де має слухати Gunicorn)
echo "🔌 Крок 6: Перевірка порту 8000"
echo "--------------------------------------"
sudo netstat -tlnp | grep :8000 || echo "❌ Нічого не слухає на порту 8000"
echo ""

# 7. ВИПРАВЛЕННЯ
echo "🔧 Крок 7: ВИПРАВЛЕННЯ"
echo "--------------------------------------"

# Перезапуск PostgreSQL
echo "🔄 Перезапускаю PostgreSQL..."
sudo systemctl restart postgresql
sleep 3
echo "✅ PostgreSQL перезапущено"
echo ""

# Зупинка всіх процесів Gunicorn (на всяк випадок)
echo "🛑 Зупиняю всі процеси Gunicorn..."
sudo pkill -9 gunicorn 2>/dev/null || echo "Процесів не знайдено"
sleep 2
echo ""

# Перезапуск сервісу ProPart
echo "🔄 Перезапускаю ProPart (Gunicorn)..."
sudo systemctl restart propart
sleep 5
echo ""

# Перезапуск Nginx
echo "🔄 Перезапускаю Nginx..."
sudo systemctl restart nginx
sleep 2
echo ""

# 8. ПЕРЕВІРКА ПІСЛЯ ВИПРАВЛЕННЯ
echo "✅ Крок 8: ПЕРЕВІРКА ПІСЛЯ ВИПРАВЛЕННЯ"
echo "--------------------------------------"

echo "🐘 PostgreSQL:"
sudo systemctl is-active postgresql && echo "✅ Працює" || echo "❌ Не працює"
echo ""

echo "🌐 Nginx:"
sudo systemctl is-active nginx && echo "✅ Працює" || echo "❌ Не працює"
echo ""

echo "🦄 Gunicorn (ProPart):"
sudo systemctl is-active propart && echo "✅ Працює" || echo "❌ Не працює"
echo ""

echo "🔌 Порт 8000:"
sudo netstat -tlnp | grep :8000 && echo "✅ Порт відкритий" || echo "❌ Порт закритий"
echo ""

# 9. Останні логи після перезапуску
echo "📋 Крок 9: Останні логи після перезапуску"
echo "--------------------------------------"
if [ -f /var/log/propart/gunicorn_error.log ]; then
    echo "🔴 Останні помилки:"
    tail -10 /var/log/propart/gunicorn_error.log
else
    echo "ℹ️ Лог-файл не знайдено"
fi
echo ""

# 10. Тест веб-запиту
echo "🌐 Крок 10: Тест веб-запиту"
echo "--------------------------------------"
echo "Тестую localhost:8000..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8000/ || echo "❌ Не вдалося підключитися"
echo ""

echo "=========================================="
echo "✅ ДІАГНОСТИКА ЗАВЕРШЕНА"
echo ""
echo "📌 НАСТУПНІ КРОКИ:"
echo "   1. Якщо всі сервіси працюють (✅) - спробуйте відкрити сайт у браузері"
echo "   2. Якщо є помилки (❌) - надішліть мені вивід цього скрипту"
echo "   3. Для детальних логів виконайте:"
echo "      sudo journalctl -u propart -n 50 --no-pager"
echo ""

