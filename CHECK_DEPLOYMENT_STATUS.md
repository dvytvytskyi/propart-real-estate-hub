# 🔍 Перевірка статусу deployment

## ⏱️ Пройшло 10 хвилин - що має бути

---

## 📋 КОМАНДИ ДЛЯ ПЕРЕВІРКИ (на сервері)

### 1. Перевірити чи працює deploy скрипт:
```bash
ps aux | grep deploy.sh
```

**Якщо показує процес** → скрипт ще працює ✅  
**Якщо нічого** → скрипт завершився (перевірте далі)

---

### 2. Перевірити чи встановився PostgreSQL:
```bash
sudo systemctl status postgresql
```

**Має бути:** `active (running)` ✅

---

### 3. Перевірити чи встановився Nginx:
```bash
sudo systemctl status nginx
```

**Має бути:** `active (running)` ✅

---

### 4. Перевірити чи створилася база даних:
```bash
sudo -u postgres psql -l | grep real_estate
```

**Має показати:** `real_estate_agents` ✅

---

### 5. Перевірити чи створився проект:
```bash
ls -la /var/www/propart/
```

**Має показати:**
```
app.py
run.py
templates/
static/
requirements.txt
...
```

---

### 6. Перевірити чи створився venv:
```bash
ls -la /var/www/propart/venv/
```

**Якщо є директорія** → venv створено ✅

---

### 7. Перевірити логи якщо були помилки:
```bash
# Останні 50 рядків виводу
journalctl -n 50

# Або якщо скрипт писав в файл
tail -100 /var/log/propart_install.log 2>/dev/null
```

---

## 🎯 ОЧІКУВАНІ РЕЗУЛЬТАТИ ЧЕРЕЗ 10 ХВИЛИН

### Має бути встановлено:
- ✅ PostgreSQL
- ✅ Nginx
- ✅ Python 3.10
- ✅ Certbot
- ✅ Git
- ✅ UFW (firewall)

### Може ще виконуватися:
- 🔄 Створення Python venv
- 🔄 Встановлення Python залежностей (pip install)
- 🔄 Налаштування Gunicorn

---

## ⚠️ МОЖЛИВІ СЦЕНАРІЇ

### Сценарій 1: Скрипт ще працює ✅
**Що бачите:** Термінал показує процес  
**Що робити:** Зачекайте ще 5-10 хвилин

### Сценарій 2: Скрипт запитує домен ❓
**Що бачите:** `Enter your domain name:`  
**Що робити:** Введіть `agent.pro-part.online`

### Сценарій 3: Скрипт запитує SSL ❓
**Що бачите:** `Do you want to setup SSL now?`  
**Що робити:** Введіть `y`

### Сценарій 4: Скрипт завершився ✅
**Що бачите:** Повернення до prompt  
**Що робити:** Перевірте статус сервісів (команди вище)

### Сценарій 5: Помилка ❌
**Що бачите:** Error message  
**Що робити:** Надішліть мені текст помилки

---

## 🚀 ШВИДКА ПЕРЕВІРКА

### Виконайте ці 3 команди на сервері:

```bash
# 1. Чи працює скрипт?
ps aux | grep deploy

# 2. Чи встановилися сервіси?
systemctl status postgresql nginx --no-pager | grep Active

# 3. Чи є файли проекту?
ls /var/www/propart/app.py
```

**Надішліть мені результати!**

---

## 💡 ТИПОВИЙ TIMELINE

```
0 min:   ✅ git clone
1 min:   ✅ apt update
2-8 min: 🔄 apt install (встановлення пакетів)
8 min:   ✅ PostgreSQL setup
10 min:  🔄 Python venv створення
12 min:  🔄 pip install залежностей
15 min:  ✅ Gunicorn налаштування
16 min:  ❓ Запит домену (ваш input)
17 min:  ✅ Nginx конфігурація
18 min:  ❓ Запит SSL (ваш input)
20 min:  🔄 Certbot отримання SSL
25 min:  ✅ Все готово!
```

**Ви зараз приблизно на 10-12 хвилині.**

---

## 📞 ЩО МНІ НАДІСЛАТИ

Виконайте на сервері і надішліть результат:

```bash
echo "=== СТАТУС DEPLOYMENT ==="
ps aux | grep deploy
echo ""
echo "=== СЕРВІСИ ==="
systemctl is-active postgresql nginx propart 2>/dev/null || echo "Сервіси ще не створені"
echo ""
echo "=== ПРОЕКТ ==="
ls /var/www/propart/*.py 2>/dev/null | head -3 || echo "Проект ще клонується"
```

**І я точно скажу на якому етапі ви зараз!** 🎯
