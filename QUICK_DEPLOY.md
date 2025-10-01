# 🚀 Швидкий Deploy ProPart Real Estate Hub

## ⚡ За 5 хвилин до production!

### Варіант 1: Автоматичний deploy (НАЙПРОСТІШИЙ)

```bash
# 1. Підключіться до сервера
ssh user@your-server-ip

# 2. Клонуйте проект
git clone <your-repo-url> propart
cd propart

# 3. Запустіть deploy скрипт
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

**Готово!** 🎉

---

### Варіант 2: Manual deploy

#### Крок 1: Підготовка сервера
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip \
    postgresql postgresql-contrib nginx git \
    certbot python3-certbot-nginx ufw
```

#### Крок 2: Налаштування PostgreSQL
```bash
sudo -u postgres psql
```
```sql
CREATE USER propart_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE real_estate_agents OWNER propart_user;
GRANT ALL PRIVILEGES ON DATABASE real_estate_agents TO propart_user;
\q
```

#### Крок 3: Налаштування проекту
```bash
# Create directories
sudo mkdir -p /var/www/propart
sudo mkdir -p /var/log/propart
sudo mkdir -p /var/run/propart

# Clone project
cd /var/www/propart
git clone <your-repo> .

# Create venv
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Крок 4: Environment variables
```bash
sudo nano /var/www/propart/.env
```
```env
SECRET_KEY=your-generated-secret-key
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://propart_user:your_password@localhost/real_estate_agents
HUBSPOT_API_KEY=your-hubspot-api-key
```

#### Крок 5: Systemd service
```bash
sudo cp propart.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable propart
sudo systemctl start propart
```

#### Крок 6: Nginx
```bash
sudo cp nginx.conf /etc/nginx/sites-available/propart
sudo ln -s /etc/nginx/sites-available/propart /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

#### Крок 7: SSL
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

#### Крок 8: Firewall
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 📋 Checklist

- [ ] Сервер з Ubuntu 20.04+
- [ ] Домен вказує на IP сервера
- [ ] SSH доступ
- [ ] Git repository готовий
- [ ] API ключі (HubSpot, etc.)

---

## 🔧 Troubleshooting

### Проблема: Service не запускається
```bash
sudo journalctl -u propart -f
```

### Проблема: Nginx помилка
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/propart_error.log
```

### Проблема: Database connection
```bash
sudo -u postgres psql -c "\l"
```

---

## 🎯 Після deployment

### Перевірити статус
```bash
sudo systemctl status propart
sudo systemctl status nginx
```

### Переглянути логи
```bash
# Application logs
sudo tail -f /var/log/propart/gunicorn.log

# Nginx logs
sudo tail -f /var/log/nginx/propart_access.log

# System logs
sudo journalctl -u propart -f
```

### Restart сервісів
```bash
# Restart application
sudo systemctl restart propart

# Restart nginx
sudo systemctl restart nginx

# Reload nginx (без downtime)
sudo systemctl reload nginx
```

---

## 🔄 Оновлення проекту

```bash
cd /var/www/propart
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart propart
```

---

## 🎉 Готово!

Ваш сайт доступний на: **https://your-domain.com**

### Корисні команди:

```bash
# Status
sudo systemctl status propart

# Logs
sudo journalctl -u propart -f

# Restart
sudo systemctl restart propart

# Backup DB
sudo /usr/local/bin/backup_propart.sh
```

