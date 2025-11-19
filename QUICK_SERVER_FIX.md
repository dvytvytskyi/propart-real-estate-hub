# ⚡ Швидке виправлення на сервері

## 🔴 Проблема
```
ModuleNotFoundError: No module named 'flask'
```

## ✅ Рішення

Скрипти потрібно запускати з **активованим віртуальним середовищем (venv)**.

---

## 📋 Команди для виконання на сервері

### Варіант 1: Використати wrapper скрипти (НАЙПРОСТІШИЙ) ⭐

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
git pull origin main
bash run_check_comment_sync.sh
bash run_sync_lead_to_hubspot.sh
sudo systemctl restart propart
```

---

### Варіант 2: Вручну з активацією venv

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
git pull origin main

# Активувати venv
source venv/bin/activate

# Перевірити лід
python3 check_comment_sync.py

# Синхронізувати лід
python3 sync_lead_to_hubspot.py

# Деактивувати venv
deactivate

# Перезапустити сервіс
sudo systemctl restart propart
```

---

### Варіант 3: Якщо venv не існує

Якщо отримуєте помилку `venv/bin/activate: No such file or directory`:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# Створити venv
python3 -m venv venv

# Активувати venv
source venv/bin/activate

# Встановити залежності
pip install --upgrade pip
pip install -r requirements.txt

# Тепер можна запускати скрипти
python3 check_comment_sync.py
python3 sync_lead_to_hubspot.py

# Деактивувати venv
deactivate

# Перезапустити сервіс
sudo systemctl restart propart
```

---

## 🎯 Одна команда (скопіюйте всю)

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub && git pull origin main && source venv/bin/activate && python3 check_comment_sync.py && python3 sync_lead_to_hubspot.py && deactivate && sudo systemctl restart propart
```

---

## 📝 Після виконання

1. Додайте новий коментар до ліда "тест комент"
2. Перевірте, чи він з'явився в HubSpot Notes
3. Перевірте логи: `sudo journalctl -u propart -f`

---

## 💡 Пояснення

- **venv** (віртуальне середовище) містить всі встановлені Python пакети (Flask, тощо)
- Без активації venv, Python не знає, де шукати ці пакети
- `source venv/bin/activate` активує venv для поточної сесії терміналу
- Після активації всі команди `python3` використовують пакети з venv

