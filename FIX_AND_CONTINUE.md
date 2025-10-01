# 🔧 Виправлення та продовження deployment

## 📊 Поточна ситуація:

- ❌ Deploy скрипт зупинився через MongoDB помилку в apt update
- ✅ Nginx працює
- ❌ PostgreSQL не встановлений (Unit postgresql.service could not be found)
- ❌ Propart service не створено

---

## 🚀 ВИПРАВЛЕННЯ (на сервері):

### Крок 1: Видаліть проблемний MongoDB репозиторій
```bash
sudo rm /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
```

### Крок 2: Запустіть deploy скрипт знову
```bash
cd /var/www/propart
sudo ./deploy.sh
```

Тепер він пройде без помилок! ✅

---

## ⚡ АБО ШВИДШЕ - Manual deployment:

Якщо deploy.sh не працює, виконайте ці команди вручну:

### 1. Видалити MongoDB repo
```bash
sudo rm /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
```

### 2. Встановити пакети
```bash
sudo apt install -y python3.10 python3.10-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx ufw
```

### 3. Налаштувати PostgreSQL
```bash
sudo -u postgres psql << EOF
CREATE USER propart_user WITH PASSWORD 'SecurePassword123!';
CREATE DATABASE real_estate_agents OWNER propart_user;
GRANT ALL PRIVILEGES ON DATABASE real_estate_agents TO propart_user;
\q
EOF
```

### 4. Створити Python venv та встановити залежності
```bash
cd /var/www/propart
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 5. Налаштувати .env
```bash
sudo nano /var/www/propart/.env
```

Додайте:
```env
SECRET_KEY=c5c143f7591aaf968a93e09d37f979b033ac0f0bcbd45b5c90fb68c71db11f60
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://propart_user:SecurePassword123!@localhost/real_estate_agents
HUBSPOT_API_KEY=ваш-hubspot-ключ
```

### 6. Ініціалізувати базу даних
```bash
source venv/bin/activate
python setup.py
```

### 7. Налаштувати systemd service
```bash
sudo cp propart.service /etc/systemd/system/
sudo mkdir -p /var/log/propart /var/run/propart
sudo chown -R www-data:www-data /var/www/propart /var/log/propart /var/run/propart
sudo systemctl daemon-reload
sudo systemctl enable propart
sudo systemctl start propart
```

### 8. Налаштувати Nginx
```bash
# Відредагувати конфігурацію
sudo nano /var/www/propart/nginx.conf
# Замініть "your-domain.com" на "agent.pro-part.online"

sudo cp /var/www/propart/nginx.conf /etc/nginx/sites-available/propart
sudo ln -s /etc/nginx/sites-available/propart /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 9. Налаштувати SSL
```bash
sudo certbot --nginx -d agent.pro-part.online -d www.agent.pro-part.online
```

### 10. Налаштувати Firewall
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

---

## ✅ Перевірка

```bash
sudo systemctl status propart
sudo systemctl status nginx
curl -I http://localhost:8000
```

---

## 🎯 Швидший варіант - виправте і перезапустіть deploy.sh:

```bash
sudo rm /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
cd /var/www/propart
sudo ./deploy.sh
```

**Це найшвидший спосіб!** 🚀

