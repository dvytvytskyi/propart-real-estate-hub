#!/bin/bash

# ========================================
# ProPart Real Estate Hub - Deploy Script
# ========================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ProPart Real Estate Hub - Deployment${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Variables
PROJECT_NAME="propart"
PROJECT_DIR="/var/www/${PROJECT_NAME}"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="/var/log/${PROJECT_NAME}"
RUN_DIR="/var/run/${PROJECT_NAME}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (use sudo)${NC}" 
   exit 1
fi

echo -e "${YELLOW}Step 1: Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "\n${YELLOW}Step 2: Installing required packages...${NC}"
apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    nginx \
    git \
    certbot \
    python3-certbot-nginx \
    ufw

echo -e "\n${YELLOW}Step 3: Creating directories...${NC}"
mkdir -p ${PROJECT_DIR}
mkdir -p ${LOG_DIR}
mkdir -p ${RUN_DIR}
mkdir -p ${PROJECT_DIR}/static
mkdir -p ${PROJECT_DIR}/uploads

echo -e "\n${YELLOW}Step 4: Setting up PostgreSQL...${NC}"
sudo -u postgres psql -c "CREATE USER propart_user WITH PASSWORD 'YOUR_DB_PASSWORD_HERE';" || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE real_estate_agents OWNER propart_user;" || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE real_estate_agents TO propart_user;"

echo -e "\n${YELLOW}Step 5: Copying project files...${NC}"
# Assuming project files are in current directory
cp -r . ${PROJECT_DIR}/
cd ${PROJECT_DIR}

echo -e "\n${YELLOW}Step 6: Creating Python virtual environment...${NC}"
python3.10 -m venv ${VENV_DIR}
source ${VENV_DIR}/bin/activate

echo -e "\n${YELLOW}Step 7: Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

echo -e "\n${YELLOW}Step 8: Setting up environment variables...${NC}"
if [ ! -f ${PROJECT_DIR}/.env ]; then
    echo -e "${RED}Creating .env file...${NC}"
    cat > ${PROJECT_DIR}/.env << EOF
# Flask Configuration
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DEBUG=False
FLASK_ENV=production

# Database Configuration
DATABASE_URL=postgresql://propart_user:YOUR_DB_PASSWORD_HERE@localhost/real_estate_agents

# HubSpot API
HUBSPOT_API_KEY=your-hubspot-api-key-here
EOF
    echo -e "${YELLOW}Please edit ${PROJECT_DIR}/.env and add your API keys!${NC}"
fi

echo -e "\n${YELLOW}Step 9: Initializing database...${NC}"
python3 setup.py

echo -e "\n${YELLOW}Step 10: Setting up Gunicorn...${NC}"
cp gunicorn_config.py ${PROJECT_DIR}/
chown -R www-data:www-data ${PROJECT_DIR}
chown -R www-data:www-data ${LOG_DIR}
chown -R www-data:www-data ${RUN_DIR}

echo -e "\n${YELLOW}Step 11: Setting up systemd service...${NC}"
cp propart.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable ${PROJECT_NAME}
systemctl restart ${PROJECT_NAME}

echo -e "\n${YELLOW}Step 12: Setting up Nginx...${NC}"
cp nginx.conf /etc/nginx/sites-available/${PROJECT_NAME}

# Update domain in nginx config
read -p "Enter your domain name (e.g., example.com): " DOMAIN
sed -i "s/your-domain.com/${DOMAIN}/g" /etc/nginx/sites-available/${PROJECT_NAME}

ln -sf /etc/nginx/sites-available/${PROJECT_NAME} /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo -e "\n${YELLOW}Step 13: Setting up firewall...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo -e "\n${YELLOW}Step 14: Setting up SSL with Let's Encrypt...${NC}"
read -p "Do you want to setup SSL now? (y/n): " SETUP_SSL
if [ "$SETUP_SSL" = "y" ]; then
    certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN}
    
    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
fi

echo -e "\n${YELLOW}Step 15: Setting up log rotation...${NC}"
cat > /etc/logrotate.d/${PROJECT_NAME} << EOF
${LOG_DIR}/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload ${PROJECT_NAME} > /dev/null 2>&1 || true
    endscript
}
EOF

echo -e "\n${YELLOW}Step 16: Setting up automated backups...${NC}"
mkdir -p /var/backups/${PROJECT_NAME}

cat > /usr/local/bin/backup_propart.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/propart"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U propart_user real_estate_agents | gzip > ${BACKUP_DIR}/db_backup_${DATE}.sql.gz
# Keep only last 7 days
find ${BACKUP_DIR} -name "db_backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup_propart.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup_propart.sh") | crontab -

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Service status:${NC}"
systemctl status ${PROJECT_NAME} --no-pager

echo -e "\n${YELLOW}Nginx status:${NC}"
systemctl status nginx --no-pager

echo -e "\n${YELLOW}Your application is now running!${NC}"
echo -e "${GREEN}URL: https://${DOMAIN}${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Edit ${PROJECT_DIR}/.env and add your API keys"
echo -e "2. Restart the service: sudo systemctl restart ${PROJECT_NAME}"
echo -e "3. Check logs: sudo journalctl -u ${PROJECT_NAME} -f"
echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "  Restart app: sudo systemctl restart ${PROJECT_NAME}"
echo -e "  View logs:   sudo journalctl -u ${PROJECT_NAME} -f"
echo -e "  Check status: sudo systemctl status ${PROJECT_NAME}"
echo -e "  Restart nginx: sudo systemctl restart nginx"
echo -e "  Backup DB:   sudo /usr/local/bin/backup_propart.sh"

echo -e "\n${GREEN}🎉 Happy hosting!${NC}\n"
