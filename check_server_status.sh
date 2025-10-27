#!/bin/bash

echo "🔍 ДІАГНОСТИКА СЕРВЕРА"
echo "======================================"
echo ""

# 1. Мережа
echo "📡 1. ПЕРЕВІРКА МЕРЕЖІ:"
echo -n "   Ping сервера: "
ping -c 1 -W 2 188.245.228.175 > /dev/null 2>&1 && echo "✅ OK" || echo "❌ FAIL"

echo -n "   PostgreSQL порт 5432: "
nc -zv 188.245.228.175 5432 2>&1 | grep -q succeeded && echo "✅ OK" || echo "❌ FAIL"
echo ""

# 2. PostgreSQL
echo "🗄️  2. ПЕРЕВІРКА PostgreSQL:"
python3 << 'EOF'
import psycopg2
try:
    conn = psycopg2.connect(
        host='188.245.228.175',
        port=5432,
        user='propart_user_estate',
        password='$u~gIi18jt535]~Bv=M~d#ivk<jkX0',
        database='propart_real_estate',
        connect_timeout=5
    )
    print('   Статус: ✅ ПРАЦЮЄ')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM "user";')
    count = cursor.fetchone()[0]
    print(f'   Користувачів: {count}')
    conn.close()
except psycopg2.OperationalError as e:
    if 'recovery' in str(e).lower():
        print('   Статус: ⚠️  RECOVERY MODE')
    else:
        print(f'   Статус: ❌ ПОМИЛКА')
    print(f'   Деталі: {str(e)[:100]}')
except Exception as e:
    print(f'   Статус: ❌ ПОМИЛКА: {e}')
EOF
echo ""

# 3. Локальна SQLite
echo "💾 3. ЛОКАЛЬНА SQLite:"
if [ -f "instance/propart.db" ]; then
    SIZE=$(du -h instance/propart.db | cut -f1)
    echo "   Файл: ✅ Існує ($SIZE)"
    python3 << 'EOF'
from app import app, db, User
with app.app_context():
    try:
        count = User.query.count()
        print(f'   Користувачів: {count}')
    except:
        print('   Користувачів: ❌ Помилка')
EOF
else
    echo "   Файл: ❌ Не знайдено"
fi
echo ""

# 4. Flask сервер
echo "🌐 4. FLASK СЕРВЕР:"
FLASK_PROCESSES=$(ps aux | grep "python run.py" | grep -v grep | wc -l)
if [ $FLASK_PROCESSES -gt 0 ]; then
    echo "   Процеси: ✅ Запущено ($FLASK_PROCESSES)"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5001/ 2>&1)
    if [ "$HTTP_CODE" == "302" ] || [ "$HTTP_CODE" == "200" ]; then
        echo "   HTTP: ✅ Відповідає ($HTTP_CODE)"
    else
        echo "   HTTP: ❌ Помилка ($HTTP_CODE)"
    fi
else
    echo "   Процеси: ❌ Не запущено"
    echo "   HTTP: ❌ Недоступний"
fi
echo ""

# 5. Конфігурація
echo "⚙️  5. КОНФІГУРАЦІЯ (.env):"
if grep -q "^DATABASE_URL=postgresql" .env 2>/dev/null; then
    echo "   БД: PostgreSQL (продакшн)"
elif grep -q "^#.*DATABASE_URL=postgresql" .env 2>/dev/null; then
    echo "   БД: SQLite (локальна)"
else
    echo "   БД: SQLite (fallback)"
fi

if grep -q "HUBSPOT_API_KEY=pat-" .env 2>/dev/null; then
    echo "   HubSpot: ✅ Налаштовано"
else
    echo "   HubSpot: ❌ Не налаштовано"
fi
echo ""

echo "======================================"
echo "✅ ДІАГНОСТИКА ЗАВЕРШЕНА"

