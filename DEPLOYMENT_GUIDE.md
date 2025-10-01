# 🚀 Гайд по деплою ProPart Real Estate Hub

## 📋 Що потрібно для deployment

### 1. **Інформація про сервер**
Мені потрібна наступна інформація:

#### Сервер:
- [ ] IP адреса сервера
- [ ] SSH доступ (username)
- [ ] SSH ключ або пароль
- [ ] Порт SSH (зазвичай 22)

#### Домен (опціонально):
- [ ] Доменне ім'я (наприклад: `propart.example.com`)
- [ ] Доступ до DNS налаштувань

#### База даних:
- [ ] PostgreSQL вже встановлено? (якщо ні - встановимо)
- [ ] Бажані credentials для БД

#### SSL сертифікат:
- [ ] Чи потрібен HTTPS? (рекомендовано)
- [ ] Let's Encrypt (безкоштовно) або власний сертифікат?

---

## 🛠️ Технології для deployment

### Рекомендований стек:

1. **Web Server:** Nginx (reverse proxy)
2. **WSGI Server:** Gunicorn
3. **Database:** PostgreSQL
4. **Process Manager:** Systemd
5. **SSL:** Let's Encrypt (Certbot)
6. **OS:** Ubuntu 20.04/22.04 LTS

---

## 📦 Що я зроблю автоматично

### 1. Підготовка проекту ✅
- [x] Створити `requirements.txt` з усіма залежностями
- [x] Додати `.env.example` з прикладами змінних
- [x] Створити конфігурацію Gunicorn
- [x] Створити конфігурацію Nginx
- [x] Створити systemd service файл
- [x] Написати deploy скрипт

### 2. На сервері (після отримання доступу):
- [ ] Встановити необхідні пакети
- [ ] Налаштувати PostgreSQL
- [ ] Створити Python virtual environment
- [ ] Встановити залежності
- [ ] Налаштувати Gunicorn
- [ ] Налаштувати Nginx
- [ ] Налаштувати SSL (Let's Encrypt)
- [ ] Налаштувати автозапуск
- [ ] Налаштувати логи
- [ ] Створити backup систему

---

## 📁 Файли для deployment

Створю наступні файли:

1. **gunicorn_config.py** - конфігурація Gunicorn
2. **nginx.conf** - конфігурація Nginx
3. **propart.service** - systemd service
4. **deploy.sh** - скрипт деплою
5. **.env.production** - production змінні
6. **supervisor.conf** - альтернатива systemd (якщо потрібно)

---

## 🔐 Безпека

### Що буде налаштовано:

- ✅ Firewall (UFW)
- ✅ Тільки необхідні порти відкриті (80, 443, SSH)
- ✅ SSL сертифікат
- ✅ Security headers в Nginx
- ✅ Rate limiting
- ✅ Безпечні права доступу до файлів
- ✅ Автоматичні backup бази даних

---

## 📊 Моніторинг та логи

### Де будуть логи:

- **Application:** `/var/log/propart/app.log`
- **Nginx Access:** `/var/log/nginx/propart_access.log`
- **Nginx Error:** `/var/log/nginx/propart_error.log`
- **Gunicorn:** `/var/log/propart/gunicorn.log`

---

## 🔄 Процес deployment

### Автоматичний:
```bash
# 1. З'єднання з сервером
ssh user@server

# 2. Клонування проекту
git clone <repository>

# 3. Запуск deploy скрипту
cd propart-hub
./deploy.sh
```

### Або я можу зробити це за вас через SSH!

---

## 💰 Вартість хостингу (орієнтовно)

### VPS варіанти:

1. **DigitalOcean** (рекомендовано)
   - Basic Droplet: $6/міс (1GB RAM)
   - Professional: $12/міс (2GB RAM)
   
2. **Hetzner Cloud**
   - CX11: €4.15/міс (2GB RAM) - найдешевше
   - CX21: €5.83/міс (4GB RAM)

3. **AWS Lightsail**
   - $5/міс (1GB RAM)
   - $10/міс (2GB RAM)

4. **Linode**
   - Nanode: $5/міс (1GB RAM)
   - Shared: $10/міс (2GB RAM)

### Рекомендація:
**Hetzner Cloud CX21 (€5.83/міс)** - найкраще співвідношення ціна/якість для України

---

## 🎯 Мінімальні вимоги до сервера

- **CPU:** 1 core (2 cores рекомендовано)
- **RAM:** 1GB мінімум (2GB рекомендовано)
- **Диск:** 20GB SSD
- **OS:** Ubuntu 20.04 або 22.04 LTS
- **Bandwidth:** Безліміт або мінімум 1TB/міс

---

## 📝 Що мені надати

### Варіант 1: У вас вже є сервер
```
SSH доступ:
- Host: 123.456.789.0
- User: ubuntu / root
- SSH Key або Password
- Port: 22

Домен (опціонально):
- example.com або subdomain.example.com
```

### Варіант 2: Потрібна допомога з вибором хостингу
Я допоможу:
1. Вибрати оптимальний хостинг
2. Зареєструватися
3. Налаштувати сервер з нуля

---

## ⚡ Швидкий старт

Якщо у вас вже є сервер, просто дайте мені:

```bash
# SSH команда для підключення
ssh user@your-server-ip

# Або якщо використовуєте ключ
ssh -i /path/to/key user@your-server-ip
```

**І я зроблю все автоматично за ~20 хвилин!** 🚀

---

## 📞 Наступні кроки

1. **Визначитеся з хостингом** (якщо ще немає)
2. **Надайте SSH доступ**
3. **Вкажіть домен** (якщо є)
4. **Я деплою проект!**

---

## 🎉 Після deployment

Ви отримаєте:
- ✅ Робочий сайт на вашому домені
- ✅ HTTPS з SSL сертифікатом
- ✅ Автоматичний перезапуск при падінні
- ✅ Логи для моніторингу
- ✅ Backup система
- ✅ Інструкції по оновленню

---

## 💡 Альтернативні варіанти

### Platform as a Service (простіше, але дорожче):

1. **Render.com** - від $7/міс
   - Автоматичний деплой з GitHub
   - SSL included
   - Easy setup

2. **Railway.app** - від $5/міс
   - GitHub integration
   - Автоматичний CI/CD

3. **Heroku** - від $7/міс
   - Classic PaaS
   - Add-ons для PostgreSQL

**Рекомендація:** Якщо хочете максимальну простоту - Render.com або Railway. Якщо хочете контроль і економію - VPS (Hetzner).

---

## 📧 Що далі?

**Напишіть мені:**
1. Який варіант обираєте? (VPS / PaaS)
2. Чи є вже сервер?
3. Чи потрібна допомога з вибором?

**І я почну deployment прямо зараз!** 🚀
