# 🔐 Налаштування безпеки ProPart Real Estate Hub

## ✅ Що було реалізовано

### 1. **Обробка помилок бази даних**
- ✅ Connection pooling з автоматичним reconnect
- ✅ Таймаути для запитів
- ✅ Глобальні error handlers
- ✅ Автоматичний rollback при помилках

### 2. **Централізоване логування**
- ✅ Ротація логів (10MB, 10 файлів)
- ✅ Різні рівні логування (INFO, WARNING, ERROR)
- ✅ Логи зберігаються в `logs/propart.log`

### 3. **HubSpot API Rate Limiting**
- ✅ Ліміт 90 requests/10 seconds (безпечно під 100)
- ✅ Автоматичний retry з exponential backoff
- ✅ Обробка 429 (Too Many Requests)

### 4. **Покращена безпека**
- ✅ CSRF захист
- ✅ Rate limiting для login (10 спроб/хвилину)
- ✅ Bcrypt для паролів (замість Werkzeug)
- ✅ Перевірка SECRET_KEY

---

## 📋 Необхідні кроки після встановлення

### 1. Оновити залежності

```bash
pip install -r requirements.txt
```

### 2. Згенерувати SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Додайте згенерований ключ в `.env` файл:

```env
SECRET_KEY=ваш-згенерований-ключ-тут
```

### 3. Налаштувати DATABASE_URL (опціонально)

Якщо база даних на іншому хості:

```env
DATABASE_URL=postgresql://username:password@host:port/database
```

### 4. Ініціалізувати Alembic (міграції)

```bash
# Ініціалізація Alembic
alembic init migrations

# Створити першу міграцію
alembic revision --autogenerate -m "Initial migration"

# Застосувати міграцію
alembic upgrade head
```

---

## 🔒 Рекомендації з безпеки

### Для Production:

1. **Завжди використовуйте сильний SECRET_KEY**
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Використовуйте HTTPS**
   - Налаштуйте SSL сертифікат
   - Використовуйте reverse proxy (nginx/Apache)

3. **Обмежте доступ до бази даних**
   - Використовуйте окремого користувача для застосунку
   - Дайте мінімальні необхідні права

4. **Регулярно оновлюйте залежності**
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   ```

5. **Моніторинг логів**
   - Регулярно перевіряйте `logs/propart.log`
   - Налаштуйте alerting для критичних помилок

---

## 📊 Моніторинг

### Перевірка логів

```bash
# Останні 50 рядків логу
tail -50 logs/propart.log

# Моніторинг в реальному часі
tail -f logs/propart.log

# Пошук помилок
grep ERROR logs/propart.log
```

### Перевірка rate limiting

Логи автоматично записують:
- Rate limit досягнуто
- 429 помилки від HubSpot
- Спроби повторних запитів

---

## 🚨 Відомі проблеми та рішення

### 1. "SECRET_KEY not set" warning

**Проблема:** SECRET_KEY не встановлено в .env

**Рішення:**
```bash
echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')" >> .env
```

### 2. Database connection errors

**Проблема:** Не можу підключитися до PostgreSQL

**Рішення:**
```bash
# Перевірте чи запущено PostgreSQL
pg_isready

# Перевірте DATABASE_URL в .env
echo $DATABASE_URL
```

### 3. HubSpot 429 errors

**Проблема:** Занадто багато запитів до HubSpot API

**Рішення:**
- Rate limiter автоматично обробляє це
- Перевірте логи для деталей
- Збільште інтервал між запитами якщо потрібно

---

## 📝 Додаткова інформація

- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [HubSpot API Rate Limits](https://developers.hubspot.com/docs/api/usage-details)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

