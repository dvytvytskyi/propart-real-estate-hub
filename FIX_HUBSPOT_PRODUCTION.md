# 🔧 Виправлення проблеми з HubSpot API на продакшені

## 🎯 Проблема
На продакшені (`agent.pro-part.online`) відображається помилка:
> "Лід додано локально. Помилка авторизації HubSpot API (недійсний ключ)."

Це означає, що `HUBSPOT_API_KEY` не встановлено або встановлено неправильно на продакшені.

---

## ✅ Рішення

### Варіант 1: Через CloudPanel UI (рекомендовано)

1. **Увійдіть в CloudPanel** → ваш сайт `agent.pro-part.online`

2. **Перейдіть в Settings** → **Environment Variables**

3. **Знайдіть або додайте змінну:**
   ```
   HUBSPOT_API_KEY=pat-your-actual-api-key-here
   ```
   ⚠️ **Замініть `pat-your-actual-api-key-here` на ваш реальний HubSpot API ключ**

4. **Збережіть зміни**

5. **Перезапустіть додаток:**
   - CloudPanel → Python Settings → **Restart Application**

---

### Варіант 2: Через SSH та .env файл

1. **Підключіться до сервера через SSH:**
   ```bash
   ssh ваш_користувач@agent.pro-part.online
   ```

2. **Знайдіть директорію проекту:**
   ```bash
   cd /home/pro-part-agent/htdocs/agent.pro-part.online
   # або
   cd /var/www/agent.pro-part.online
   # або інша директорія залежно від вашого налаштування
   ```

3. **Перевірте чи існує .env файл:**
   ```bash
   ls -la .env
   ```

4. **Відредагуйте або створіть .env файл:**
   ```bash
   nano .env
   # або
   vi .env
   ```

5. **Додайте або оновіть HUBSPOT_API_KEY:**
   ```env
   HUBSPOT_API_KEY=pat-your-actual-api-key-here
   ```
   ⚠️ **Замініть на ваш реальний API ключ!**

6. **Збережіть файл** (Ctrl+O, Enter, Ctrl+X для nano)

7. **Перезапустіть додаток:**
   ```bash
   # Якщо використовується systemd:
   sudo systemctl restart propart
   
   # Або через CloudPanel:
   # Python Settings → Restart Application
   ```

---

## 🔍 Як отримати HubSpot API ключ

1. **Увійдіть в HubSpot** → [app.hubspot.com](https://app.hubspot.com)

2. **Settings** → **Integrations** → **Private Apps**

3. **Створіть новий Private App** (якщо ще не маєте):
   - Назва: "Real Estate Agents Hub"
   - Права доступу:
     - ✅ **Contacts**: Read, Write
     - ✅ **Deals**: Read, Write

4. **Скопіюйте API ключ** (починається з `pat-`)

---

## 🧪 Перевірка налаштування

### 1. Використайте діагностичний ендпоінт:

Відкрийте в браузері (після входу як адміністратор):
```
https://agent.pro-part.online/api/diagnostic
```

Ви повинні побачити:
```json
{
  "environment": {
    "hubspot": {
      "api_key_set": true,
      "client_configured": true,
      "connection_test": "success"
    }
  }
}
```

### 2. Перевірте через логування:

Після перезапуску додатка, перевірте логи:
```bash
# В CloudPanel:
# Application Logs

# Або через SSH:
tail -f /var/log/propart/app.log
# або
journalctl -u propart -f
```

Шукайте повідомлення:
```
✅ HubSpot API успішно підключено!
```

---

## 🚨 Якщо проблема залишається

### Перевірте:

1. **Чи правильно скопійовано API ключ?**
   - Має починатися з `pat-`
   - Не містить пробілів або переносів рядків

2. **Чи перезапущено додаток після додавання змінної?**
   - Змінні середовища завантажуються тільки під час старту

3. **Чи є доступ до HubSpot API?**
   - Перевірте права Private App в HubSpot
   - Перевірте чи не заблоковано аккаунт HubSpot

4. **Перевірте формат .env файлу:**
   ```env
   # Правильно:
   HUBSPOT_API_KEY=pat-na1-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxxx
   
   # Неправильно:
   HUBSPOT_API_KEY = pat-na1-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxxx  # пробіли
   HUBSPOT_API_KEY="pat-na1-xxxx-xxxx-xxxx-xxxxxxxxxxxx-xxxxx"  # лапки не потрібні
   ```

---

## 📝 Після налаштування

1. **Спробуйте додати лід** через форму на `agent.pro-part.online/add_lead`

2. **Перевірте чи зникає попередження**

3. **Перевірте чи створюються контакти в HubSpot**

---

## ✅ Очікуваний результат

Після правильного налаштування:
- ✅ Лід зберігається локально (вже працює)
- ✅ Лід синхронізується з HubSpot
- ✅ Створюються контакт та угода в HubSpot
- ✅ Немає попереджень про помилки HubSpot API

---

**Примітка:** Локально все працює тому, що у вас є правильний `HUBSPOT_API_KEY` в локальному `.env` файлі. Потрібно просто скопіювати той самий ключ на продакшен.

