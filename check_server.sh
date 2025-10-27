#!/bin/bash

echo "🔍 ДІАГНОСТИКА СЕРВЕРА"
echo "=========================================="
echo ""

# 1. Диск
echo "💾 Диск:"
df -h / | tail -1
echo ""

# 2. Swap та RAM
echo "🧠 Пам'ять:"
free -h
echo ""

# 3. Топ-5 процесів по пам'яті
echo "📊 Топ-5 процесів по RAM:"
ps aux --sort=-%mem | head -6
echo ""

# 4. PostgreSQL статус
echo "🐘 PostgreSQL статус:"
systemctl status postgresql --no-pager | grep -E "Active:|Loaded:|Main PID" | head -3
echo ""

# 5. PostgreSQL процеси
echo "🐘 PostgreSQL процеси:"
ps aux | grep postgres | grep -v grep | wc -l
echo "   процесів запущено"
echo ""

# 6. Перезапустити PostgreSQL
echo "🔄 Перезапускаю PostgreSQL..."
systemctl restart postgresql
sleep 5

echo "✅ PostgreSQL перезапущено"
echo ""

# 7. Новий статус
echo "🐘 Новий статус PostgreSQL:"
systemctl status postgresql --no-pager | grep -E "Active:|Loaded:|Main PID" | head -3
echo ""

# 8. Перевірити підключення
echo "🔌 Тест підключення до PostgreSQL:"
sudo -u postgres psql -c "SELECT version();" 2>&1 | head -3
echo ""

# 9. Перевірити recovery
echo "🔍 Перевірка recovery mode:"
sudo -u postgres psql -c "SELECT pg_is_in_recovery();" 2>&1 | grep -E "pg_is_in_recovery|f|t"
echo ""

echo "=========================================="
echo "✅ ДІАГНОСТИКА ЗАВЕРШЕНА"

