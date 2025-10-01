#!/bin/bash

# ========================================
# Простий deploy для Ubuntu 24.04
# ========================================

set -e

echo "🚀 ProPart Hub - Simple Deployment"
echo "===================================="

# 1. Встановити пакети
echo "📦 Встановлення пакетів..."
apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx git ufw

# 2. Налаштувати PostgreSQL
echo "🗄️ Налаштування PostgreSQL..."
sudo -u postgres psql << EOF
SELECT 'CREATE USER propart_user WITH PASSWORD '"'SecurePass123!'"'' WHERE NOT EXISTS (SELECT FROM pg_user WHERE usename = 'propart_user')\gexec
SELECT 'CREATE DATABASE real_estate_agents OWNER propart_user' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'real_estate_agents')\gexec
GRANT ALL PRIVILEGES ON DATABASE real_estate_agents TO propart_user;
EOF

# 3. Створити venv та встановити залежності
echo "🐍 Створення Python environment..."
cd /var/www/propart
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 4. Налаштувати .env
echo "⚙️ Налаштування .env..."
cat > /var/www/propart/.env << EOF
SECRET_KEY=c5c143f7591aaf968a93e09d37f979b033ac0f0bcbd45b5c90fb68c71db11f60
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://propart_user:SecurePass123!@localhost/real_estate_agents
HUBSPOT_API_KEY=your-key-here
EOF

# 5. Ініціалізувати базу
echo "🗄️ Ініціалізація бази даних..."
source venv/bin/activate
python setup.py

# 6. Налаштувати директорії та права
echo "📁 Налаштування прав..."
mkdir -p /var/log/propart /var/run/propart
chown -R www-data:www-data /var/www/propart /var/log/propart /var/run/propart

# 7. Налаштувати systemd
echo "⚙️ Налаштування systemd service..."
cp propart.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable propart
systemctl start propart

# 8. Налаштувати Nginx
echo "🌐 Налаштування Nginx..."
read -p "Введіть ваш домен (наприклад agent.pro-part.online): " DOMAIN
sed "s/your-domain.com/$DOMAIN/g" nginx.conf > /etc/nginx/sites-available/propart
ln -sf /etc/nginx/sites-available/propart /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 9. Налаштувати SSL
echo "🔒 Налаштування SSL..."
read -p "Налаштувати SSL? (y/n): " SETUP_SSL
if [ "$SETUP_SSL" = "y" ]; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || echo "⚠️ SSL помилка (можливо DNS ще не готовий)"
fi

# 10. Firewall
echo "🛡️ Налаштування firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

echo ""
echo "✅ Deployment завершено!"
echo ""
echo "Перевірте:"
echo "  sudo systemctl status propart"
echo "  https://$DOMAIN"
echo ""

