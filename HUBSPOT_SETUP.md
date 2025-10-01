# 🔗 Налаштування HubSpot API

## Крок 1: Отримання API ключа

1. **Увійдіть в HubSpot** → [app.hubspot.com](https://app.hubspot.com)

2. **Перейдіть в Settings** → Integrations → Private Apps

3. **Створіть новий Private App:**
   - Натисніть "Create a private app"
   - Назва: "Real Estate Agents Hub"
   - Опис: "API для синхронізації лідів"

4. **Налаштуйте права доступу:**
   - **Contacts**: Read, Write
   - **Deals**: Read, Write
   - **Companies**: Read (опціонально)

5. **Скопіюйте API ключ** (починається з `pat-`)

## Крок 2: Налаштування змінних середовища

1. **Створіть файл `.env`** в корені проекту:

```bash
# HubSpot API Configuration
HUBSPOT_API_KEY=pat-your-api-key-here

# Flask Configuration
SECRET_KEY=your-secret-key-here
```

2. **Замініть `pat-your-api-key-here`** на ваш реальний API ключ

## Крок 3: Тестування підключення

Запустіть тестовий скрипт:

```bash
python test_hubspot.py
```

Якщо все налаштовано правильно, ви побачите:
```
✅ HubSpot API підключення успішне!
📊 Знайдено контактів: X
✅ Тестовий контакт створено: 12345
🗑️ Тестовий контакт видалено
```

## Крок 4: Перезапуск додатку

Після налаштування API ключа перезапустіть Flask додаток:

```bash
python -c "from app import app; app.run(debug=True, host='0.0.0.0', port=5003)"
```

## Що синхронізується з HubSpot:

### При створенні ліда:
- ✅ **Контакт** з email, телефоном, ім'ям
- ✅ **Угода** з назвою, бюджетом, типом

### При додаванні нотатки:
- ✅ **Оновлення контакту** з нотаткою та часом активності

### При зміні статусу:
- ✅ **Оновлення статусу** контакту в HubSpot

## Можливі помилки:

### 401 Unauthorized
- Перевірте правильність API ключа
- Переконайтеся, що API ключ активний

### 403 Forbidden
- Перевірте права доступу Private App
- Переконайтеся, що дозволено Read/Write для Contacts та Deals

### 429 Too Many Requests
- API має ліміти на кількість запитів
- Зачекайте кілька хвилин перед повторним тестуванням

## Корисні посилання:

- [HubSpot API Documentation](https://developers.hubspot.com/docs/api/overview)
- [Private Apps Guide](https://developers.hubspot.com/docs/api/private-apps)
- [Contacts API](https://developers.hubspot.com/docs/api/crm/contacts)
- [Deals API](https://developers.hubspot.com/docs/api/crm/deals)