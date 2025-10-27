#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# 🚀 ФІНАЛЬНИЙ DEPLOY
# ═══════════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════════════════"
echo "🚀 DEPLOY: Обов'язковий вибір адміна"
echo "════════════════════════════════════════════════════════════"
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# 1. Git pull
echo "1️⃣ Оновлення коду з Git..."
git pull origin main
echo "✅ Код оновлено"
echo ""

# 2. Міграція БД
echo "2️⃣ Міграція бази даних (додавання поля admin_id)..."
venv/bin/python3 migrate_add_admin_field.py
echo "✅ Міграція виконана"
echo ""

# 3. Створення адмінів
echo "3️⃣ Створення адмінів..."
venv/bin/python3 << 'PYTHON'
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admins_data = [
        ('anton_admin', 'anton@pro-part.online', 'sfajerfe234ewqf#'),
        ('alex_admin', 'alex@pro-part.online', 'dgerifwef@fmso4'),
    ]
    
    created = 0
    for username, email, password in admins_data:
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            print(f"   ⚠️  {username} вже існує")
            continue
        
        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='admin',
            is_verified=True
        )
        db.session.add(admin)
        print(f"   ✅ {username} створено")
        created += 1
    
    db.session.commit()
    
    if created > 0:
        print(f"\n✅ Створено {created} нових адмінів")
    
    # Показати всіх адмінів
    all_admins = User.query.filter_by(role='admin').all()
    print(f"\n📋 Всього адмінів в системі: {len(all_admins)}")
    for admin in all_admins:
        print(f"   - {admin.username} ({admin.email})")
PYTHON

echo ""
echo "✅ Адміни готові"
echo ""

# 4. Перезапуск
echo "4️⃣ Перезапуск додатку..."
pkill -f "python.*run.py"
sleep 2

nohup venv/bin/python run.py > logs/propart.log 2>&1 &
sleep 4

# 5. Перевірка
echo ""
echo "5️⃣ Перевірка статусу..."
if ps aux | grep "python.*run.py" | grep -v grep > /dev/null; then
    echo "✅ Додаток працює"
    ps aux | grep "python.*run.py" | grep -v grep | head -2
else
    echo "❌ Додаток НЕ запущений!"
    echo "Логи:"
    tail -20 logs/propart.log
    exit 1
fi

if netstat -tulpn 2>/dev/null | grep -q 8090; then
    echo "✅ Порт 8090 відкритий"
else
    echo "⚠️  Порт 8090 не відповідає"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ DEPLOY ЗАВЕРШЕНО!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Відкрийте: https://agent.pro-part.online/register"
echo ""
echo "🔐 Адміни:"
echo "   - anton_admin / sfajerfe234ewqf#"
echo "   - alex_admin / dgerifwef@fmso4"
echo ""
echo "✨ Тепер при реєстрації ОБОВ'ЯЗКОВО треба вибрати адміна!"
echo ""

