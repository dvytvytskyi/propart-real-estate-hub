# 🚀 ЗАПУСК ЗАРАЗ - Покрокова інструкція

## ✅ DNS налаштовано - можна деплоїти!

---

## 📋 КОМАНДИ ДЛЯ ВИКОНАННЯ НА СЕРВЕРІ

### Підключіться до сервера:
```bash
ssh root@188.245.228.175
# або
ssh ubuntu@188.245.228.175
```

---

### Після підключення виконайте ПО ЧЕРЗІ:

## 1️⃣ Клонування проекту
```bash
git clone https://github.com/dvytvytskyi/propart-real-estate-hub.git /var/www/propart
```

## 2️⃣ Перехід в директорію
```bash
cd /var/www/propart
```

## 3️⃣ Надання прав
```bash
sudo chmod +x deploy.sh
```

## 4️⃣ Запуск deployment (ГОЛОВНИЙ КРОК)
```bash
sudo ./deploy.sh
```

---

## ⚠️ ПІД ЧАС ВИКОНАННЯ:

### Скрипт запитає домен:
```
Enter your domain name (e.g., example.com): 
```
**ВВЕДІТЬ:** `agent.pro-part.online`

### Скрипт запитає про SSL:
```
Do you want to setup SSL now? (y/n):
```
**ВВЕДІТЬ:** `y`

---

## 5️⃣ Після завершення deployment:

### Налаштуйте .env файл:
```bash
sudo nano /var/www/propart/.env
```

### Знайдіть та змініть:
```env
# Було:
DATABASE_URL=postgresql://propart_user:YOUR_DB_PASSWORD_HERE@localhost/real_estate_agents

# Стане (вигадайте складний пароль):
DATABASE_URL=postgresql://propart_user:MySecurePassword123!@localhost/real_estate_agents

# Також додайте HubSpot ключ:
HUBSPOT_API_KEY=ваш-реальний-hubspot-ключ
```

**Збережіть:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 6️⃣ Перезапустіть сервіс:
```bash
sudo systemctl restart propart
```

## 7️⃣ Перевірте статус:
```bash
sudo systemctl status propart
```

Має бути: **active (running)** ✅

---

## 8️⃣ Перевірте в браузері:

Відкрийте: **https://agent.pro-part.online**

### Логін для тесту:
- **Username:** admin
- **Password:** admin123

---

## 🔧 Якщо щось не працює:

### Перегляньте логи:
```bash
# Application logs
sudo journalctl -u propart -f

# Nginx logs
sudo tail -f /var/log/nginx/propart_error.log
```

### Перезапустіть все:
```bash
sudo systemctl restart propart
sudo systemctl restart nginx
sudo systemctl restart postgresql
```

---

## ⏱️ Час виконання:

- **Кроки 1-3:** ~1 хвилина
- **Крок 4 (deploy.sh):** ~15-20 хвилин
- **Кроки 5-6:** ~2 хвилини
- **Всього:** ~20-25 хвилин

---

## 🎯 Очікуваний результат:

```
✅ PostgreSQL налаштовано
✅ Python venv створено
✅ Залежності встановлено
✅ База даних ініціалізована
✅ Gunicorn запущено
✅ Nginx налаштовано
✅ SSL сертифікат отримано
✅ Firewall налаштовано
✅ Автоматичні backup активні
```

---

## 🎉 ГОТОВО!

**Ваш сайт працюватиме на: https://agent.pro-part.online**

---

## 📞 Потрібна допомога?

Якщо виникли проблеми на будь-якому кроці - напишіть мені:
- На якому кроці застрягли
- Що показує помилка
- Що показують логи

**Я допоможу вирішити!** 🚀

