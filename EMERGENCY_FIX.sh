#!/bin/bash
# ════════════════════════════════════════════════════════════════
# 🚨 ЕКСТРЕННЕ ВИПРАВЛЕННЯ
# ════════════════════════════════════════════════════════════════

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

echo "════════════════════════════════════════════════════════════"
echo "🚨 ЕКСТРЕННЕ ВИПРАВЛЕННЯ"
echo "════════════════════════════════════════════════════════════"

# 1. Зупинити все
echo ""
echo "1️⃣ Зупинка..."
pkill -f "python.*run.py" 2>/dev/null || true
sleep 3

# 2. Git pull
echo "2️⃣ Git pull..."
git pull origin main 2>&1 | tail -3

# 3. Показати що в логах ЗАРАЗ
echo ""
echo "3️⃣ Поточні логи (останні 30 рядків):"
echo "────────────────────────────────────────────────────────────"
tail -30 logs/propart.log 2>/dev/null || echo "Логів немає"
echo "────────────────────────────────────────────────────────────"

# 4. Тест запуску Python (перевірка синтаксису)
echo ""
echo "4️⃣ Тест Python..."
venv/bin/python3 -c "from app import app; print('✅ Імпорт OK')" 2>&1 || echo "❌ Помилка імпорту"

# 5. Створити адмінів (без помилок)
echo ""
echo "5️⃣ Створення адмінів..."
venv/bin/python3 << 'ENDPYTHON' 2>&1 || echo "❌ Помилка створення адмінів"
import os, sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

try:
    from app import app, db, User
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        # Створити таблиці
        db.create_all()
        
        # Адміни
        for username, email, pwd in [
            ('anton_admin', 'anton@pro-part.online', 'sfajerfe234ewqf#'),
            ('alex_admin', 'alex@pro-part.online', 'dgerifwef@fmso4'),
        ]:
            if not User.query.filter((User.username == username) | (User.email == email)).first():
                u = User(username=username, email=email, 
                        password_hash=generate_password_hash(pwd), 
                        role='admin', is_verified=True)
                db.session.add(u)
                print(f"✅ {username}")
            else:
                print(f"⚠️  {username} вже є")
        
        db.session.commit()
        print(f"✅ Адмінів: {User.query.filter_by(role='admin').count()}")
except Exception as e:
    print(f"❌ Помилка: {e}")
    import traceback
    traceback.print_exc()
ENDPYTHON

# 6. Запуск з виведенням помилок
echo ""
echo "6️⃣ Запуск додатку..."
nohup venv/bin/python run.py > logs/propart.log 2>&1 &
PYTHON_PID=$!
echo "   PID: $PYTHON_PID"

# Чекаємо 6 секунд
for i in {6..1}; do
    echo -n "   Чекаємо $i сек..."
    sleep 1
    echo -e "\r\033[K"
done

# 7. Перевірка
echo ""
echo "7️⃣ Перевірка:"
if ps aux | grep "python.*run.py" | grep -v grep > /dev/null; then
    echo "✅ Python працює"
    ps aux | grep "python.*run.py" | grep -v grep | head -1
else
    echo "❌ Python НЕ працює!"
fi

if netstat -tulpn 2>/dev/null | grep -q 8090; then
    echo "✅ Порт 8090 відкритий"
else
    echo "❌ Порт 8090 закритий"
fi

# 8. НОВІ логи (що сталося після запуску)
echo ""
echo "8️⃣ НОВІ логи (останні 40 рядків):"
echo "────────────────────────────────────────────────────────────"
tail -40 logs/propart.log
echo "────────────────────────────────────────────────────────────"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "🔍 ДІАГНОСТИКА ЗАВЕРШЕНА"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Спробуйте: https://agent.pro-part.online/register"
echo ""

