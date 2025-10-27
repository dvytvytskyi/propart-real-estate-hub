# ✅ ГОТОВО ДО ДЕПЛОЮ НА ПРОДАКШН

**Дата:** 27 жовтня 2025
**Статус:** 🟢 READY TO DEPLOY

---

## 👥 НОВІ АДМІНІСТРАТОРИ СТВОРЕНІ

### **1. Anton Admin**
```
Username: anton_admin
Email:    anton@propart.com
Password: sfajerfe234ewqf#
Role:     admin
Status:   ✅ Verified
```

### **2. Alex Admin**
```
Username: alex_admin
Email:    alex@propart.com
Password: dgerifwef@fmso4
Role:     admin
Status:   ✅ Verified
```

### **3. Існуючий Admin**
```
Username: admin
Email:    admin@propart.com
Password: admin123
Role:     admin
Status:   ✅ Verified
```

---

## 🚀 ЗМІНИ ЗАПУШЕНІ ДО GIT

### **Коміт:** `ad582c3`

### **Основні виправлення:**

✅ **HubSpot Stage ID**
- Замінено застарілі stage ID на валідні
- Створення лідів працює без помилки (400)

✅ **Завантаження файлів для нерухомості**
- Фото та документи тепер завантажуються
- Підтримка S3 та локального зберігання

✅ **Міграція бази даних**
- PostgreSQL: 135.181.201.185:5432 (crmdb)
- Всі таблиці створено та працюють

✅ **UI/UX покращення**
- Форма створення нерухомості
- Сторінка перегляду проекту
- Профіль користувача (SaaS стиль)
- Кастомна модалка планування

---

## 📋 ІНСТРУКЦІЯ ДЕПЛОЮ НА ПРОДАКШН

### **Крок 1: Підключення до сервера**

```bash
ssh root@188.245.228.175
```

### **Крок 2: Перехід до директорії проекту**

```bash
cd /path/to/propart-real-estate-hub
```

### **Крок 3: Пул останніх змін**

```bash
git pull origin main
```

### **Крок 4: Створення нових адміністраторів на продакшн**

```bash
python3 << 'EOF'
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Anton Admin
    if not User.query.filter_by(username='anton_admin').first():
        anton = User(
            username='anton_admin',
            email='anton@propart.com',
            password_hash=generate_password_hash('sfajerfe234ewqf#'),
            role='admin',
            is_verified=True
        )
        db.session.add(anton)
        print("✅ anton_admin створено")
    
    # Alex Admin
    if not User.query.filter_by(username='alex_admin').first():
        alex = User(
            username='alex_admin',
            email='alex@propart.com',
            password_hash=generate_password_hash('dgerifwef@fmso4'),
            role='admin',
            is_verified=True
        )
        db.session.add(alex)
        print("✅ alex_admin створено")
    
    db.session.commit()
    print("🎉 Адміністратори створені на продакшн!")
EOF
```

### **Крок 5: Перезапуск додатку**

#### **Якщо використовується systemd:**

```bash
systemctl restart propart
systemctl status propart
```

#### **Якщо використовується gunicorn напряму:**

```bash
pkill -f gunicorn
gunicorn --config gunicorn_config.py wsgi:app
```

#### **Якщо використовується Docker:**

```bash
docker-compose restart
```

### **Крок 6: Перевірка деплою**

```bash
# Перевірити статус
curl -I https://your-domain.com

# Перевірити логи
tail -50 /var/log/propart/propart.log
# або
journalctl -u propart -n 50
```

---

## 🔐 ДОСТУП ДО ПРОДАКШН

### **URL:**
```
https://your-domain.com
```

### **Увійти як:**

**Anton Admin:**
- Username: `anton_admin`
- Password: `sfajerfe234ewqf#`

**Alex Admin:**
- Username: `alex_admin`
- Password: `dgerifwef@fmso4`

**Головний Admin:**
- Username: `admin`
- Password: `admin123`

---

## 📊 КОНФІГУРАЦІЯ ПРОДАКШН

### **База даних:**
```
Host:     135.181.201.185
Port:     5432
Database: crmdb
User:     postgres
```

### **HubSpot API:**
```
Status: ✅ Підключено
Valid Stage IDs: 3204738258, 3204738259, 3204738261, 3204738262, 3204738265, 3204738266, 3204738267
```

### **S3 Storage:**
```
Bucket:  pro-part-hub
Region:  eu-west-3
Fallback: Локальне зберігання (/static/uploads/)
```

---

## ✅ CHECKLIST ПІСЛЯ ДЕПЛОЮ

- [ ] Сервер запущено без помилок
- [ ] База даних підключена
- [ ] HubSpot API працює
- [ ] Можна увійти як anton_admin
- [ ] Можна увійти як alex_admin
- [ ] Створення лідів працює
- [ ] Створення нерухомості працює
- [ ] Завантаження фото працює
- [ ] Завантаження документів працює
- [ ] Синхронізація з HubSpot працює

---

## 🆘 TROUBLESHOOTING

### **Якщо база даних не підключається:**

```bash
# Перевірити статус PostgreSQL
systemctl status postgresql

# Перезапустити PostgreSQL
systemctl restart postgresql

# Перевірити логи
tail -50 /var/log/postgresql/postgresql-*.log
```

### **Якщо HubSpot не працює:**

```bash
# Перевірити .env файл
cat .env | grep HUBSPOT_API_KEY

# Перевірити валідні stage ID в app.py
grep -A 10 "3204738258" app.py
```

### **Якщо файли не завантажуються:**

```bash
# Перевірити S3 credentials
cat .env | grep AWS

# Перевірити локальну папку uploads
ls -lah static/uploads/
chmod -R 755 static/uploads/
```

---

## 📝 ВАЖЛИВО

⚠️ **Після деплою на продакшн:**

1. ✅ Змініть паролі адміністраторів на більш складні
2. ✅ Налаштуйте HTTPS (якщо ще не налаштовано)
3. ✅ Налаштуйте автоматичні бекапи бази даних
4. ✅ Налаштуйте моніторинг (uptime, errors)
5. ✅ Перевірте всі критичні функції

---

## 🎯 ГОТОВО!

Всі зміни запушені та готові до деплою на продакшн!

**Git repository:** https://github.com/dvytvytskyi/propart-real-estate-hub

**Останній коміт:** `ad582c3` - "🎉 Критичні виправлення та покращення"

---

**Підготував:** AI Assistant
**Дата:** 27 жовтня 2025

