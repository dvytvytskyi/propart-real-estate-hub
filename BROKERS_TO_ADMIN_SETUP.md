# 👥 ПРИВ'ЯЗКА БРОКЕРІВ ДО АДМІНІВ

## ✅ ЩО ЗРОБЛЕНО:

### 1️⃣ **Модель User**
- Додано поле `admin_id` - ID адміна для брокерів
- Додано relationship `brokers` - список брокерів адміна
- Додано relationship `admin` - адмін брокера

### 2️⃣ **Реєстрація**
- При реєстрації **обов'язково** вибирається адмін
- Dropdown з усіма адмінами системи
- Без вибору адміна реєстрація неможлива

### 3️⃣ **Профіль адміна**
- Блок "Мої брокери" з переліком усіх брокерів
- Статистика по кожному брокеру:
  - Кількість лідів
  - Кількість угод
  - Статус верифікації

### 4️⃣ **Dashboard адміна**
- Адмін бачить **тільки** лідів своїх брокерів
- Метрики враховують тільки лідів його брокерів
- Фільтрація працює автоматично

---

## 📋 ІНСТРУКЦІЇ ДЛЯ ДЕПЛОЮ

### **Крок 1: SSH на сервер**
```bash
ssh root@188.245.228.175
```

### **Крок 2: Перейти до проекту**
```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
```

### **Крок 3: Оновити код**
```bash
git pull origin main
```

### **Крок 4: Міграція бази даних**
```bash
# Додати поле admin_id до таблиці user
venv/bin/python3 migrate_add_admin_field.py
```

### **Крок 5: Видалити лідів (якщо потрібно)**
```bash
# ОПЦІОНАЛЬНО: Якщо хочете почати з чистої бази
venv/bin/python3 delete_all_leads.py
```

### **Крок 6: Перезапустити додаток**
```bash
pkill -f "python.*run.py"
sleep 2
nohup venv/bin/python run.py > logs/propart.log 2>&1 &
sleep 4
```

### **Крок 7: Перевірка**
```bash
ps aux | grep "python.*run.py" | grep -v grep
netstat -tulpn | grep 8090
tail -20 logs/propart.log
```

---

## 🎯 ЯК ПРАЦЮЄ

### **Для нових користувачів:**
1. Йдуть на /register
2. Заповнюють форму
3. **Вибирають адміна зі списку** (обов'язково!)
4. Реєструються

### **Для адмінів:**
1. Заходять у профіль
2. Бачать блок "Мої брокери"
3. Бачать статистику кожного брокера
4. У dashboard бачать тільки лідів своїх брокерів

### **Для брокерів:**
- Працюють як зазвичай
- Прив'язані до свого адміна
- Їх ліди відображаються у їхнього адміна

---

## 🔧 ПРИКЛАД ВИКОРИСТАННЯ

### **Створити адміна (на сервері):**
```python
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        username='manager_john',
        email='john@pro-part.online',
        password_hash=generate_password_hash('securepassword'),
        role='admin',
        is_verified=True
    )
    db.session.add(admin)
    db.session.commit()
    print(f"✅ Адмін створений: ID {admin.id}")
```

### **Прив'язати існуючого брокера до адміна:**
```python
from app import app, db, User

with app.app_context():
    broker = User.query.filter_by(username='broker_name').first()
    admin = User.query.filter_by(username='manager_john').first()
    
    if broker and admin:
        broker.admin_id = admin.id
        db.session.commit()
        print(f"✅ Брокер {broker.username} прив'язаний до {admin.username}")
```

---

## 📊 СТРУКТУРА БД

```
User:
├── id (primary key)
├── username
├── email
├── role ('admin' | 'agent')
├── admin_id (foreign key → User.id)  ← НОВЕ ПОЛЕ
└── relationships:
    ├── brokers (User[])    ← Список брокерів адміна
    └── admin (User)        ← Адмін брокера

Lead:
├── id
├── agent_id (foreign key → User.id)
└── ...
```

---

## ⚠️ ВАЖЛИВО

1. **Адміни не мають admin_id** - це поле тільки для брокерів
2. **Брокери обов'язково** мають admin_id
3. **Старі брокери** (без admin_id) - треба вручну прив'язати
4. **Адміни бачать тільки** лідів своїх брокерів

---

## 🚀 ГОТОВО!

Після виконання інструкцій:
- ✅ Брокери прив'язані до адмінів
- ✅ Адміни бачать своїх брокерів у профілі
- ✅ Dashboard адміна показує тільки лідів його брокерів
- ✅ Реєстрація вимагає вибору адміна

**Перевірте:** https://agent.pro-part.online

