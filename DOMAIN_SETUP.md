# 🌐 Налаштування домену для ProPart Real Estate Hub

## 📍 Куди направляти домен

Ваш домен має вказувати на **IP адресу вашого сервера**.

---

## 🎯 Крок 1: Дізнайтеся IP сервера

```bash
# На вашому сервері виконайте:
curl ifconfig.me

# Або
hostname -I | awk '{print $1}'
```

Це поверне щось на зразок: `123.456.789.012`

---

## 🎯 Крок 2: Налаштування DNS записів

### У вашого реєстратора доменів (наприклад: GoDaddy, Namecheap, CloudFlare)

Додайте **два A-записи:**

```
Тип  | Ім'я/Host    | Значення (Value)        | TTL
-----|--------------|------------------------|------
A    | @            | 123.456.789.012        | 3600
A    | www          | 123.456.789.012        | 3600
```

**Де:**
- `@` - це root домен (example.com)
- `www` - це www піддомен (www.example.com)
- `123.456.789.012` - замініть на IP вашого сервера
- `TTL` - час кешування (3600 = 1 година)

---

## 📋 Приклади налаштування для різних провайдерів

### GoDaddy:
1. Увійдіть в GoDaddy
2. Мої продукти → Домени → DNS
3. Додайте два A-записи:
   - Host: `@`, Points to: `ваш-IP`
   - Host: `www`, Points to: `ваш-IP`
4. Збережіть

### Namecheap:
1. Domain List → Manage → Advanced DNS
2. Add New Record:
   - Type: `A Record`, Host: `@`, Value: `ваш-IP`
   - Type: `A Record`, Host: `www`, Value: `ваш-IP`
3. Save

### CloudFlare (рекомендовано для швидкості):
1. DNS → Add record
2. Type: `A`, Name: `@`, Content: `ваш-IP`, Proxy: ✅ (помаранчева хмара)
3. Type: `A`, Name: `www`, Content: `ваш-IP`, Proxy: ✅
4. Save

---

## ⏱️ Час поширення DNS

**Важливо:** DNS записи потребують часу для поширення:
- **Мінімум:** 15-30 хвилин
- **Зазвичай:** 1-2 години  
- **Максимум:** 24-48 годин

### Перевірка готовності:
```bash
# На вашому комп'ютері
nslookup your-domain.com

# Або
dig your-domain.com +short
```

Має повернути IP вашого сервера.

---

## 🔧 Приклад повної конфігурації DNS

```
Тип   | Ім'я        | Значення              | TTL  | Примітка
------|-------------|----------------------|------|------------------
A     | @           | 123.456.789.012      | 3600 | Root домен
A     | www         | 123.456.789.012      | 3600 | WWW піддомен
CNAME | mail        | @                    | 3600 | Опціонально
MX    | @           | mail.example.com     | 3600 | Опціонально (пошта)
TXT   | @           | "v=spf1 ..."         | 3600 | Опціонально (SPF)
```

**Для базового запуску потрібні тільки 2 перші A-записи!**

---

## 🚀 Після налаштування DNS

### 1. Дочекайтеся поширення (15-30 хв)

### 2. На сервері запустіть deployment:
```bash
cd /var/www/propart
sudo ./deploy.sh
```

### 3. Скрипт запитає домен:
```
Enter your domain name (e.g., example.com): 
```
Введіть: `your-domain.com` (БЕЗ www)

### 4. SSL налаштується автоматично:
```
Do you want to setup SSL now? (y/n): y
```

Let's Encrypt автоматично:
- Отримає SSL сертифікат
- Налаштує HTTPS
- Налаштує auto-renewal

---

## ✅ Готово!

Ваш сайт буде доступний за адресами:
- ✅ `https://your-domain.com`
- ✅ `https://www.your-domain.com`
- ✅ HTTP автоматично redirect на HTTPS

---

## 🔍 Troubleshooting

### Проблема 1: DNS не поширився
```bash
# Перевірте DNS
nslookup your-domain.com

# Якщо повертає старий IP - зачекайте ще
```

### Проблема 2: SSL помилка
```bash
# Переконайтеся що DNS вказує на правильний IP
dig your-domain.com +short

# Спробуйте SSL знову
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### Проблема 3: "Connection refused"
```bash
# Перевірте firewall
sudo ufw status

# Має бути:
# 80/tcp  ALLOW
# 443/tcp ALLOW

# Якщо ні:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## 🎯 Швидкий чеклист

- [ ] Отримав IP адресу сервера
- [ ] Додав A-запис: `@` → IP сервера
- [ ] Додав A-запис: `www` → IP сервера
- [ ] Зачекав 15-30 хвилин
- [ ] Перевірив DNS: `nslookup your-domain.com`
- [ ] Запустив deploy.sh на сервері
- [ ] Ввів домен при запиті
- [ ] Налаштував SSL (y)
- [ ] Відкрив `https://your-domain.com` 🎉

---

## 💡 CloudFlare (додатково, але рекомендовано)

### Переваги:
- ✅ Безкоштовний SSL
- ✅ CDN для швидкості
- ✅ DDoS захист
- ✅ Кешування
- ✅ Analytics

### Налаштування:
1. Зареєструйтеся на cloudflare.com
2. Додайте ваш домен
3. Змініть nameservers у реєстратора на CloudFlare nameservers
4. DNS буде керуватися через CloudFlare
5. Увімкніть помаранчеву хмару (Proxy) для записів

---

## 📞 Підтримка

Якщо виникли проблеми:
1. Перевірте DNS: `nslookup your-domain.com`
2. Перевірте чи сервер доступний: `ping your-domain.com`
3. Перевірте логи: `sudo journalctl -u propart -f`

**Пишіть якщо потрібна допомога!** 🚀

---

## 🎉 Після успішного налаштування

Ваш ProPart Real Estate Hub буде доступний:
- 🌐 https://your-domain.com
- 🔒 SSL захищено
- ⚡ Швидко
- 🛡️ Безпечно

**Вітаю з успішним deployment!** 🎊

