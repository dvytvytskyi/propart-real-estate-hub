# 🏢 ProPart Real Estate Hub

Система управління лідами для агентів нерухомості з інтеграцією HubSpot.

## ✨ Основні можливості

- 📊 **Dashboard** з аналітикою лідів
- ➕ **Управління лідами** - додавання, редагування, відстеження
- 🔄 **Інтеграція з HubSpot** - автоматична синхронізація
- 👤 **Система користувачів** - агенти та адміністратори
- ✅ **Верифікація агентів** - система підтвердження
- 🏆 **Геймфікація** - поінти та рівні для агентів
- 📱 **Responsive дизайн** - працює на всіх пристроях

## 🛠️ Технології

- **Backend:** Python 3.10, Flask 2.3
- **Database:** PostgreSQL
- **Frontend:** Bootstrap 5, JavaScript
- **WSGI Server:** Gunicorn
- **Web Server:** Nginx
- **Authentication:** Flask-Login, Bcrypt
- **API Integration:** HubSpot API

## 🚀 Швидкий старт (Development)

### 1. Клонування репозиторію
```bash
git clone <repository-url>
cd propart-hub
```

### 2. Встановлення залежностей
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# або
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Налаштування .env
```bash
cp .env.example .env
# Відредагуйте .env файл з вашими налаштуваннями
```

### 4. Ініціалізація бази даних
```bash
python setup.py
```

### 5. Запуск
```bash
python run.py
```

Відкрийте http://localhost:5001

### Тестові облікові записи
- **Адмін:** admin / admin123
- **Агент:** agent / agent123

## 🌐 Production Deployment

### Автоматичний deployment (рекомендовано)
```bash
# На сервері
git clone <repository-url> /var/www/propart
cd /var/www/propart
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

Детальніше: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

### Швидкий deployment
Дивіться [QUICK_DEPLOY.md](QUICK_DEPLOY.md)

## 📋 Вимоги

- Python 3.10+
- PostgreSQL 12+
- Nginx (для production)
- SSL сертифікат (для HTTPS)

## 🔐 Безпека

- ✅ Bcrypt для паролів
- ✅ Rate limiting
- ✅ CSRF захист (готовий до активації)
- ✅ SQL injection захист
- ✅ XSS захист
- ✅ Security headers

Детальніше: [SECURITY_SETUP.md](SECURITY_SETUP.md)

## 📊 Структура проекту

```
propart-hub/
├── app.py              # Головний файл застосунку
├── run.py              # Entry point
├── setup.py            # Ініціалізація БД
├── requirements.txt    # Python залежності
├── templates/          # HTML шаблони
│   ├── base.html
│   ├── dashboard.html
│   ├── profile.html
│   └── components/     # Переusable компоненти
├── static/            # Static файли
│   ├── css/
│   └── js/
├── logs/              # Логи застосунку
├── gunicorn_config.py # Gunicorn конфігурація
├── nginx.conf         # Nginx конфігурація
└── propart.service    # Systemd service

```

## 📝 Документація

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Повний гайд по deployment
- [Quick Deploy](QUICK_DEPLOY.md) - Швидкий старт
- [Security Setup](SECURITY_SETUP.md) - Налаштування безпеки
- [Critical Fixes](CRITICAL_FIXES_IMPLEMENTED.md) - Виправлені проблеми

## 🔄 Оновлення

```bash
cd /var/www/propart
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart propart
```

## 📊 Логи та моніторинг

```bash
# Application logs
sudo tail -f /var/log/propart/app.log

# Gunicorn logs
sudo tail -f /var/log/propart/gunicorn.log

# Nginx logs
sudo tail -f /var/log/nginx/propart_error.log

# System logs
sudo journalctl -u propart -f
```

## 🛠️ Корисні команди

```bash
# Restart application
sudo systemctl restart propart

# Check status
sudo systemctl status propart

# Reload nginx
sudo systemctl reload nginx

# Backup database
sudo /usr/local/bin/backup_propart.sh
```

## 🤝 Contributing

1. Fork проект
2. Створіть feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit зміни (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Відкрийте Pull Request

## 📄 License

Цей проект є приватним і належить ProPart Real Estate.

## 📞 Підтримка

При виникненні проблем:
1. Перевірте [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Перегляньте логи
3. Створіть issue

## 🎉 Особливості

- **Rate Limiting** - захист від brute force атак
- **HubSpot Integration** - автоматичний sync з rate limiting
- **Логування** - централізоване з ротацією
- **Backup** - автоматичні щоденні backup бази даних
- **SSL** - Let's Encrypt з auto-renewal
- **Firewall** - UFW налаштований
- **Systemd** - автоматичний restart при падінні

## 🚀 Roadmap

- [ ] Додати CSRF токени у всі форми
- [ ] Alembic міграції
- [ ] API endpoints для мобільного додатку
- [ ] Email нотифікації
- [ ] SMS інтеграція
- [ ] Advanced analytics
- [ ] Export звітів

---

Made with ❤️ for ProPart Real Estate
