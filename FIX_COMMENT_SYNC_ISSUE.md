# 🔧 Виправлення проблеми синхронізації коментарів з HubSpot Notes

## ❌ Проблема
Коментарі не додаються в HubSpot Notes, хоча раніше працювали.

---

## 🔍 Крок 1: Діагностика на сервері

Виконайте на сервері:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
source venv/bin/activate
python3 diagnose_comment_sync.py
deactivate
```

Це покаже:
- Чи встановлено HUBSPOT_API_KEY
- Скільки коментарів не синхронізовано
- Які умови не виконуються

---

## 🔍 Крок 2: Перевірка логів після додавання коментаря

Додайте новий коментар до ліда "тест комент", потім перевірте логи:

```bash
sudo journalctl -u propart -f --since "5 minutes ago" | grep -i "comment\|note\|hubspot"
```

Шукайте:
- `📝 Створюється нотатка в HubSpot`
- `✅ Нотатка створена в HubSpot`
- `❌ Помилка створення нотатки`
- `⚠️ Лід не має hubspot_deal_id`

---

## 🔍 Крок 3: Перевірка умов синхронізації

Коментар синхронізується ТІЛЬКИ якщо:
1. ✅ Лід має `hubspot_deal_id`
2. ✅ `hubspot_client` ініціалізовано
3. ✅ `HUBSPOT_API_KEY` встановлено

Перевірте:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
source venv/bin/activate
python3 << 'EOF'
from app import app, db, Lead
with app.app_context():
    test_lead = Lead.query.filter(Lead.deal_name.like("%тест%")).first()
    if test_lead:
        print(f"Лід: {test_lead.deal_name}")
        print(f"hubspot_deal_id: {test_lead.hubspot_deal_id or '❌ НЕ ВСТАНОВЛЕНО'}")
    else:
        print("❌ Лід 'тест комент' не знайдено")
EOF
deactivate
```

---

## ✅ Рішення

### Варіант 1: Лід не має hubspot_deal_id

Якщо лід не має `hubspot_deal_id`, синхронізуйте його:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
source venv/bin/activate
python3 sync_lead_to_hubspot.py
deactivate
```

### Варіант 2: HUBSPOT_API_KEY не встановлено

Перевірте `.env` файл:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
cat .env | grep HUBSPOT_API_KEY
```

Якщо ключ відсутній або неправильний, додайте/оновіть його:

```bash
nano .env
# Додайте або оновіть:
HUBSPOT_API_KEY=ваш-реальний-ключ

# Перезапустіть сервіс
sudo systemctl restart propart
```

### Варіант 3: Помилка API HubSpot

Якщо в логах є помилки API (наприклад, 401, 403, 429), перевірте:
- Чи правильний API ключ
- Чи не перевищено rate limit
- Чи не змінився формат API

---

## 🧪 Тестування

Після виправлення:

1. Додайте новий коментар до ліда "тест комент"
2. Перевірте логи:
   ```bash
   sudo journalctl -u propart -f | grep -i "note\|comment"
   ```
3. Перевірте в HubSpot, чи з'явилася нотатка
4. Перевірте в базі даних:
   ```bash
   cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
   source venv/bin/activate
   python3 check_comment_sync.py
   deactivate
   ```

---

## 📋 Швидка перевірка (всі команди разом)

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub && \
source venv/bin/activate && \
python3 diagnose_comment_sync.py && \
python3 check_comment_sync.py && \
deactivate
```

---

## 💡 Найчастіші причини

1. **Лід не має hubspot_deal_id** - найчастіша причина
2. **HUBSPOT_API_KEY не встановлено або неправильний**
3. **Помилка API HubSpot** (rate limit, невалідний ключ, тощо)
4. **Помилка в коді** (після останніх змін)

---

## 🔄 Якщо нічого не допомагає

1. Перевірте повні логи:
   ```bash
   sudo journalctl -u propart -n 1000 | grep -i "comment\|note\|hubspot"
   ```

2. Спробуйте створити нотатку вручну через HubSpot API:
   ```bash
   # (використайте diagnose_comment_sync.py для отримання API ключа та deal_id)
   curl -X POST "https://api.hubapi.com/crm/v3/objects/notes" \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "properties": {
         "hs_note_body": "Test note",
         "hs_timestamp": "2024-01-01T00:00:00Z"
       }
     }'
   ```

3. Перевірте, чи не змінився формат API HubSpot

