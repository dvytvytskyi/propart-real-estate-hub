# 🚀 Шпаргалка: Deployment на сервер

## ⚡ Швидкі команди для deployment

### Крок 1: Отримайте IP сервера
```bash
# На сервері:
curl ifconfig.me
```
Результат: `123.456.789.012` ← ця адреса потрібна для DNS

---

### Крок 2: Налаштуйте DNS (у реєстратора домену)

**Додайте 2 A-записи:**

| Тип | Ім'я | Значення |
|-----|------|----------|
| A   | @    | ваш-IP   |
| A   | www  | ваш-IP   |

**Зачекайте 15-30 хвилин** для поширення DNS.

**Перевірка:**
```bash
# На вашому комп'ютері
nslookup your-domain.com
# Має показати ваш IP
```

---

### Крок 3: Клонуйте проект на сервер

```bash
# На сервері:
git clone git@github.com:dvytvytskyi/propart-real-estate-hub.git /var/www/propart

# Або через HTTPS якщо немає SSH ключа:
git clone https://github.com/dvytvytskyi/propart-real-estate-hub.git /var/www/propart
```

---

### Крок 4: Запустіть deploy скрипт

```bash
cd /var/www/propart
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

**Скрипт запитає:**
```
Enter your domain name (e.g., example.com): your-domain.com
Do you want to setup SSL now? (y/n): y
```

**Вводьте ваш домен БЕЗ "https://" і БЕЗ "www"**  
Приклад: `propart.com.ua` або `hub.propart.com`

---

### Крок 5: Налаштуйте .env файл

```bash
sudo nano /var/www/propart/.env
```

**Додайте:**
```env
SECRET_KEY=ваш-згенерований-ключ
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://propart_user:PASSWORD@localhost/real_estate_agents
HUBSPOT_API_KEY=ваш-hubspot-ключ
```

**Збережіть:** Ctrl+O, Enter, Ctrl+X

---

### Крок 6: Перезапустіть сервіс

```bash
sudo systemctl restart propart
sudo systemctl restart nginx
```

---

### Крок 7: Перевірте статус

```bash
sudo systemctl status propart
sudo systemctl status nginx
```

**Має бути:** `active (running)` ✅

---

## 🎉 ГОТОВО!

Відкрийте в браузері: **https://your-domain.com**

---

## 📊 Корисні команди після deployment

### Перегляд логів:
```bash
# Application logs
sudo tail -f /var/log/propart/gunicorn.log

# Error logs
sudo journalctl -u propart -f

# Nginx errors
sudo tail -f /var/log/nginx/propart_error.log
```

### Restart сервісів:
```bash
# Restart застосунку
sudo systemctl restart propart

# Reload nginx (без downtime)
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx
```

### Перевірка статусу:
```bash
sudo systemctl status propart
sudo systemctl status nginx
sudo systemctl status postgresql
```

### Firewall:
```bash
# Перевірити
sudo ufw status

# Відкрити порт якщо потрібно
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## 🔧 Troubleshooting

### Проблема: Сайт не відкривається

**1. Перевірте DNS:**
```bash
nslookup your-domain.com
# Має показати IP сервера
```

**2. Перевірте сервіси:**
```bash
sudo systemctl status propart
sudo systemctl status nginx
```

**3. Перевірте firewall:**
```bash
sudo ufw status
# Має бути: 80/tcp ALLOW, 443/tcp ALLOW
```

**4. Перевірте логи:**
```bash
sudo journalctl -u propart -n 50
sudo tail -f /var/log/nginx/propart_error.log
```

---

### Проблема: SSL помилка

```bash
# Переконайтеся що DNS працює
dig your-domain.com +short

# Спробуйте SSL знову
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Перевірте сертифікат
sudo certbot certificates
```

---

### Проблема: 502 Bad Gateway

**Причина:** Gunicorn не працює

**Рішення:**
```bash
sudo systemctl restart propart
sudo journalctl -u propart -f
```

---

### Проблема: 500 Internal Server Error

**Причина:** Помилка в застосунку

**Рішення:**
```bash
# Перевірте логи
sudo tail -f /var/log/propart/gunicorn.log

# Перевірте .env файл
sudo cat /var/www/propart/.env

# Перевірте database connection
sudo -u postgres psql -c "\l"
```

---

## 📋 Швидкий чеклист

### Перед deployment:
- [ ] Отримав IP сервера
- [ ] Налаштував DNS A-записи
- [ ] Зачекав 15-30 хвилин
- [ ] Перевірив DNS: `nslookup domain.com`

### Під час deployment:
- [ ] Клонував проект: `git clone ...`
- [ ] Запустив: `sudo ./deploy.sh`
- [ ] Ввів домен без www
- [ ] Налаштував SSL (y)
- [ ] Відредагував .env файл
- [ ] Перезапустив: `sudo systemctl restart propart`

### Після deployment:
- [ ] Перевірив статус: `sudo systemctl status propart`
- [ ] Відкрив сайт: `https://domain.com`
- [ ] Залогінився в систему
- [ ] Перевірив функціонал

---

## 🎯 Типова конфігурація

### Для домену: `propart.com.ua`

**DNS записи:**
```
A    @    → 123.456.789.012
A    www  → 123.456.789.012
```

**При deployment введіть:**
```
Domain: propart.com.ua
SSL: y
```

**Результат:**
- ✅ http://propart.com.ua → https://propart.com.ua
- ✅ http://www.propart.com.ua → https://www.propart.com.ua
- ✅ Автоматичний HTTPS redirect

---

## 🌐 Альтернатива: Піддомен

Якщо використовуєте піддомен (наприклад: `hub.propart.com`):

**DNS:**
```
A    hub  → 123.456.789.012
```

**При deployment:**
```
Domain: hub.propart.com
```

---

## 💡 Рекомендації

1. **Використовуйте CloudFlare** для DNS:
   - Безкоштовний CDN
   - DDoS захист
   - Швидше поширення DNS
   - Web Application Firewall

2. **Налаштуйте SSL одразу:**
   - Безкоштовно через Let's Encrypt
   - Автоматичне оновлення
   - Краще для SEO

3. **Backup:**
   - Автоматичні backup вже налаштовані
   - Щодня о 2:00 AM
   - Зберігаються 7 днів

---

## 📞 Потрібна допомога?

**Напишіть:**
- Ваш домен
- IP сервера
- Де застрягли

**І я допоможу!** 🚀

---

## 🎊 Після успішного deployment

Ви матимете:
- ✅ Робочий сайт на вашому домені
- ✅ HTTPS з автоматичним оновленням
- ✅ Автоматичні backup БД
- ✅ Логування та моніторинг
- ✅ Auto-restart при падінні
- ✅ Firewall налаштовано

**Вітаю з запуском!** 🎉

