# 🔧 Виправлення помилки на продакшні

## Проблема
На сервері `agent.pro-part.online` виникає помилка "Ой! Щось пішло не так".

## Найімовірніші причини
1. ❌ Зміни не задеплоєні на сервері
2. ❌ Відсутня колонка `admin_id` в таблиці `user` на продакшн БД
3. ❌ Старий код Gunicorn працює з кешем

## ⚡ ШВИДКЕ РІШЕННЯ

### Варіант 1: Через SSH
```bash
# Підключитися до сервера
ssh your_user@agent.pro-part.online

# Перейти в директорію проекту
cd /path/to/propart-real-estate-hub

# Запустити скрипт оновлення
chmod +x QUICK_UPDATE_SERVER.sh
./QUICK_UPDATE_SERVER.sh
```

### Варіант 2: Ручні команди на сервері
```bash
# 1. Завантажити зміни з Git
git pull origin main

# 2. Активувати віртуальне середовище
source venv/bin/activate

# 3. Оновити залежності
pip install -r requirements.txt

# 4. ВАЖЛИВО: Перевірити/додати колонку admin_id
python3 << EOF
from app import app, db, User
with app.app_context():
    # Перевірка структури БД
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('user')]
    print("📋 Колонки в таблиці user:", columns)
    
    if 'admin_id' not in columns:
        print("❌ Колонка admin_id відсутня! Додаємо...")
        db.engine.execute('ALTER TABLE "user" ADD COLUMN admin_id INTEGER REFERENCES "user"(id)')
        print("✅ Колонку admin_id додано!")
    else:
        print("✅ Колонка admin_id вже існує")
EOF

# 5. Перезапустити Gunicorn
sudo systemctl restart propart
# АБО (якщо немає systemd)
pkill -f gunicorn
gunicorn -c gunicorn_config.py wsgi:app --daemon

# 6. Перевірити статус
sudo systemctl status propart
# АБО
ps aux | grep gunicorn

# 7. Перевірити логи
tail -f logs/propart.log
```

### Варіант 3: Міграція БД окремо
```bash
# На сервері
cd /path/to/propart-real-estate-hub
source venv/bin/activate

# Створити міграцію
python3 migrate_add_admin_field.py
```

## 🔍 Діагностика

### Перевірити логи на сервері
```bash
# Системні логи
sudo journalctl -u propart -n 100 --no-pager

# Логи додатку
tail -f logs/propart.log

# Логи Nginx
sudo tail -f /var/log/nginx/error.log
```

### Перевірити статус сервісів
```bash
sudo systemctl status propart
sudo systemctl status nginx
```

### Перевірити з'єднання з БД
```bash
python3 << EOF
from app import app, db
with app.app_context():
    try:
        db.session.execute('SELECT 1')
        print("✅ З'єднання з БД OK")
    except Exception as e:
        print(f"❌ Помилка з'єднання з БД: {e}")
EOF
```

## 📝 Що було змінено (і треба задеплоїти)
1. ✅ Додано поле `admin_id` в форму реєстрації
2. ✅ Оновлено сайдбар (додано пункт "Нерухомість")
3. ✅ Виправлено стиль кнопки "Додати лід"
4. ✅ Оновлено хедер секції "Нерухомість"
5. ✅ Додано відображення адміна в списку користувачів

## ⚠️ ВАЖЛИВО!
Переконайтеся, що на сервері:
- ✅ Є колонка `admin_id` в таблиці `user`
- ✅ Всі адміни мають `role='admin'`
- ✅ Gunicorn перезапущено після оновлення коду

## 🆘 Якщо нічого не допомагає
```bash
# Крайній випадок - повний перезапуск
sudo systemctl stop propart
pkill -9 -f gunicorn
sleep 5
sudo systemctl start propart
sudo systemctl status propart
```

