# 🖥️ Команди для виконання на сервері

## ✅ Підключення до сервера

```bash
ssh root@188.245.228.175
# Пароль: 7NdMqCMV4wtw
```

---

## 📋 Покрокові команди

### 1️⃣ Перехід до проекту

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
```

### 2️⃣ Оновлення коду

```bash
git pull origin main
```

### 3️⃣ Активація віртуального середовища та перевірка лідів

**ВАЖЛИВО:** Завжди активуйте venv перед запуском Python скриптів!

```bash
# Активувати venv
source venv/bin/activate

# Перевірити лід "тест комент"
python3 check_comment_sync.py

# Якщо у ліда немає hubspot_deal_id, синхронізуйте його
python3 sync_lead_to_hubspot.py

# Деактивувати venv (опціонально)
deactivate
```

### 4️⃣ Перезапуск додатку

```bash
sudo systemctl restart propart
```

### 5️⃣ Перевірка статусу

```bash
sudo systemctl status propart
```

### 6️⃣ Перегляд логів

```bash
sudo journalctl -u propart -f
```

---

## 🚀 Швидкий варіант (всі команди разом)

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub && \
git pull origin main && \
source venv/bin/activate && \
python3 check_comment_sync.py && \
python3 sync_lead_to_hubspot.py && \
deactivate && \
sudo systemctl restart propart
```

---

## ⚠️ Якщо venv не знайдено

Якщо ви отримуєте помилку `source: venv/bin/activate: No such file or directory`, потрібно створити venv:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

---

## 🔍 Перевірка, чи venv існує

```bash
ls -la /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/venv/bin/activate
```

Якщо файл існує - venv створено правильно ✅

