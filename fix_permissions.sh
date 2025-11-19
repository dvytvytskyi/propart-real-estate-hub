#!/bin/bash

# Виправлення прав доступу для systemd service

PROJECT_DIR="/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub"

echo "🔐 Налаштування прав доступу для www-data..."
echo ""

# 1. Надаємо права на читання/виконання для всіх батьківських директорій
echo "1️⃣ Налаштування прав для батьківських директорій..."
sudo chmod 755 /home
sudo chmod 755 /home/pro-part-agent
sudo chmod 755 /home/pro-part-agent/htdocs
sudo chmod 755 /home/pro-part-agent/htdocs/agent.pro-part.online
echo "   ✅ Права налаштовано"
echo ""

# 2. Надаємо права на проект
echo "2️⃣ Налаштування прав для проекту..."
sudo chmod -R 755 "$PROJECT_DIR"
sudo chown -R www-data:www-data "$PROJECT_DIR"
echo "   ✅ Права налаштовано"
echo ""

# 3. Перевірка прав
echo "3️⃣ Перевірка прав доступу..."
ls -ld /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
echo ""

echo "✅ Права доступу налаштовано!"
echo ""
echo "💡 Тепер спробуйте перезапустити сервіс:"
echo "   sudo systemctl restart propart"

