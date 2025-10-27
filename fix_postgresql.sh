#!/bin/bash

echo "🔧 ДІАГНОСТИКА ТА ВИПРАВЛЕННЯ PostgreSQL"
echo "=========================================="
echo ""

# 1. Перевірка стану диска
echo "1️⃣ Стан диска:"
df -h / | tail -1
echo ""

# 2. Перевірка swap
echo "2️⃣ Використання Swap:"
free -h | grep Swap
echo ""

# 3. Статус PostgreSQL
echo "3️⃣ Статус PostgreSQL:"
systemctl status postgresql --no-pager | head -15
echo ""

# 4. Перевірка recovery mode
echo "4️⃣ Перевірка recovery mode:"
sudo -u postgres psql -c "SELECT pg_is_in_recovery();" 2>&1 | head -5
echo ""

# 5. Останні помилки в логах
echo "5️⃣ Останні помилки PostgreSQL:"
tail -20 /var/log/postgresql/postgresql-*.log | grep -E "ERROR|FATAL|recovery" | tail -10
echo ""

echo "=========================================="
echo "📋 РЕКОМЕНДОВАНІ ДІЇ:"
echo ""

# Перевірка чи треба перезапускати
if systemctl is-active postgresql > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL працює, але може бути в recovery mode"
    echo ""
    echo "Спробуйте перезапустити:"
    echo "  systemctl restart postgresql"
    echo ""
    echo "Якщо не допомагає - примусове відновлення:"
    echo "  systemctl stop postgresql"
    echo "  sudo -u postgres /usr/lib/postgresql/*/bin/pg_resetwal /var/lib/postgresql/*/main"
    echo "  systemctl start postgresql"
else
    echo "❌ PostgreSQL НЕ працює!"
    echo ""
    echo "Запустіть:"
    echo "  systemctl start postgresql"
fi

echo ""
echo "=========================================="

