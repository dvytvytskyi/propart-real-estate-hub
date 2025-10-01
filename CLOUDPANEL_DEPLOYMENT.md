# ☁️ CloudPanel Deployment Guide

## 🎯 CloudPanel - це простіше ніж ручний deployment!

CloudPanel вже має вбудовану підтримку Python/Flask, тому багато кроків автоматизовані.

---

## 📋 ПОКРОКОВИЙ ПЛАН

### ✅ Крок 1: DNS (вже зроблено!)
```
A    agent.pro-part.online  →  188.245.228.175
A    www.agent.pro-part.online  →  188.245.228.175
```

---

### 🔐 Крок 2: Підключення по SSH

```bash
ssh pro-part-agent@188.245.228.175
# Введіть ваш збережений пароль
```

---

### 📁 Крок 3: Перейти в директорію сайту

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/
```

---

### 📥 Крок 4: Завантажити код з GitHub

```bash
# Спочатку очистити директорію (якщо там щось є)
rm -rf * .[^.]*

# Клонувати проект в поточну директорію
git clone https://github.com/dvytvytskyi/propart-real-estate-hub.git .
```

**Важливо:** Крапка `.` в кінці означає "клонувати в поточну директорію"

---

### 🐍 Крок 5: Створити віртуальне середовище

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 📦 Крок 6: Встановити залежності

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

**Час:** ~5-7 хвилин

---

### ⚙️ Крок 7: Налаштувати базу даних PostgreSQL

CloudPanel має вбудований PostgreSQL. Створіть базу через інтерфейс або через командну лінію:

```bash
# Через CloudPanel UI:
# Databases → Create Database
# Name: real_estate_agents
# User: propart_user
# Password: SecurePass123!

# Або через CLI:
clpctl db:add --databaseName=real_estate_agents --databaseUserName=propart_user --databaseUserPassword=SecurePass123!
```

---

### 📝 Крок 8: Ініціалізувати базу даних

```bash
source venv/bin/activate
python setup.py
```

---

### ☁️ Крок 9: Налаштування в CloudPanel UI

#### 9.1. Зайдіть в налаштування сайту `agent.pro-part.online`

#### 9.2. Python Application Settings:

**Entry Point:**
```
app:app
```

**Python Executable:** (автоматично)
```
/home/pro-part-agent/htdocs/agent.pro-part.online/venv/bin/python
```

**Application Root:**
```
/home/pro-part-agent/htdocs/agent.pro-part.online
```

#### 9.3. Environment Variables:

Додайте ці змінні в CloudPanel (Settings → Environment Variables):

```
SECRET_KEY=c5c143f7591aaf968a93e09d37f979b033ac0f0bcbd45b5c90fb68c71db11f60
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://propart_user:SecurePass123!@localhost/real_estate_agents
HUBSPOT_API_KEY=your-hubspot-api-key-here
```

**Або створіть .env файл:**
```bash
cat > /home/pro-part-agent/htdocs/agent.pro-part.online/.env << 'EOF'
SECRET_KEY=c5c143f7591aaf968a93e09d37f979b033ac0f0bcbd45b5c90fb68c71db11f60
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://propart_user:SecurePass123!@localhost/real_estate_agents
HUBSPOT_API_KEY=your-hubspot-api-key-here
EOF
```

---

### 🚀 Крок 10: Запустити додаток

В CloudPanel UI:
1. Перейдіть в **Python Settings**
2. Натисніть **Restart Application**
3. Або **Start Application** якщо ще не запущено

---

## ✅ ПЕРЕВІРКА

### 1. Статус в CloudPanel:
- Application Status: ✅ **Running**

### 2. Перевірка через браузер:
```
https://agent.pro-part.online
```

### 3. Логи в CloudPanel:
- Application Logs → Перегляньте на помилки

---

## 🔧 НАЛАШТУВАННЯ SSL В CLOUDPANEL

CloudPanel автоматично налаштовує SSL через Let's Encrypt:

1. Перейдіть в **SSL/TLS**
2. Виберіть **Let's Encrypt**
3. Введіть email
4. Натисніть **Install**
5. ✅ SSL сертифікат встановиться автоматично!

---

## 📊 СТРУКТУРА ДЛЯ CLOUDPANEL

```
/home/pro-part-agent/htdocs/agent.pro-part.online/
├── app.py                  ← Головний Flask файл
├── run.py                  ← Entry point
├── venv/                   ← Virtual environment
├── templates/              ← HTML templates
├── static/                 ← CSS/JS
├── .env                    ← Environment variables
└── requirements.txt        ← Dependencies
```

---

## 🎯 ВАЖЛИВІ МОМЕНТИ ДЛЯ CLOUDPANEL

### 1. Entry Point має бути:
```
app:app
```
Де:
- Перший `app` = файл `app.py`
- Другий `app` = Flask instance в app.py

### 2. Python Path:
CloudPanel автоматично знайде venv

### 3. WSGI Server:
CloudPanel використовує Gunicorn автоматично

---

## 🔍 TROUBLESHOOTING

### Якщо застосунок не запускається:

#### 1. Перевірте логи в CloudPanel:
```
Application Logs → Error Log
```

#### 2. Перевірте через SSH:
```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/
source venv/bin/activate
python app.py
```

#### 3. Перевірте .env:
```bash
cat .env
```

---

## ✅ ШВИДКИЙ ЧЕКЛИСТ

- [ ] SSH підключення працює
- [ ] Код клоновано в `/home/pro-part-agent/htdocs/agent.pro-part.online/`
- [ ] Virtual environment створено (`venv/`)
- [ ] Залежності встановлені (`pip install -r requirements.txt`)
- [ ] База даних створена (через CloudPanel або CLI)
- [ ] База ініціалізована (`python setup.py`)
- [ ] .env файл створено з правильними змінними
- [ ] Entry Point: `app:app` в CloudPanel
- [ ] Application перезапущено в CloudPanel
- [ ] SSL налаштовано (Let's Encrypt)
- [ ] Сайт відкривається: `https://agent.pro-part.online`

---

## 🚀 ГОТОВО ДО ЗАПУСКУ!

**CloudPanel спрощує процес - не потрібно налаштовувати Nginx, Gunicorn, systemd вручну!**

Просто:
1. Клонуйте код
2. Створіть venv
3. Встановіть залежності
4. Налаштуйте в UI CloudPanel
5. ✅ Працює!

**Удачі з deployment!** 🎉

