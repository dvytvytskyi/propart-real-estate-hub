#!/bin/bash

# ========================================
# Ручне налаштування Gunicorn
# ========================================

echo "🚀 Налаштування Gunicorn для ProPart Hub"
echo "========================================"

# 1. Створити необхідні директорії
echo "📁 Створення директорій..."
sudo mkdir -p /var/log/propart
sudo mkdir -p /var/run/propart
sudo mkdir -p /var/www/propart

# 2. Встановити Python та Gunicorn
echo "📦 Встановлення Python та Gunicorn..."
cd /var/www/propart
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 3. Тестовий запуск Gunicorn
echo "🧪 Тестовий запуск Gunicorn..."
gunicorn --bind 127.0.0.1:8000 --workers 3 --timeout 60 run:app --daemon

# Перевірка
sleep 2
curl -I http://127.0.0.1:8000

# 4. Зупинити тестовий процес
pkill -f gunicorn

# 5. Налаштувати права
echo "🔐 Налаштування прав..."
sudo chown -R www-data:www-data /var/www/propart
sudo chown -R www-data:www-data /var/log/propart
sudo chown -R www-data:www-data /var/run/propart

# 6. Створити systemd service
echo "⚙️ Налаштування systemd..."
sudo cp propart.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable propart
sudo systemctl start propart

# 7. Перевірка
echo "✅ Перевірка статусу..."
sudo systemctl status propart --no-pager

echo ""
echo "Gunicorn налаштовано!"
echo "Перевірте: curl -I http://localhost:8000"

