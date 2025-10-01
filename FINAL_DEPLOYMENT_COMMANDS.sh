#!/bin/bash

# ========================================
# ФІНАЛЬНІ КОМАНДИ ДЛЯ DEPLOYMENT
# Просто скопіюйте та виконайте на сервері!
# ========================================

echo "🚀 ProPart Real Estate Hub - Deployment"
echo "========================================"
echo ""

# Крок 1: Клонування проекту
echo "📥 Крок 1: Клонування проекту з GitHub..."
git clone https://github.com/dvytvytskyi/propart-real-estate-hub.git /var/www/propart

# Крок 2: Перехід в директорію
echo "📂 Крок 2: Перехід в директорію проекту..."
cd /var/www/propart

# Крок 3: Надання прав на виконання deploy скрипту
echo "🔧 Крок 3: Налаштування прав..."
sudo chmod +x deploy.sh

# Крок 4: Запуск автоматичного deployment
echo "🚀 Крок 4: Запуск автоматичного deployment..."
echo ""
echo "⚠️  УВАГА: Скрипт запитає:"
echo "   1. Ваш домен (введіть: agent.pro-part.online)"
echo "   2. Налаштувати SSL? (введіть: y)"
echo ""
echo "Запускаємо..."
sudo ./deploy.sh

echo ""
echo "✅ Deployment завершено!"
echo ""
echo "📋 Наступні кроки:"
echo "1. Перевірте статус: sudo systemctl status propart"
echo "2. Перегляньте логи: sudo journalctl -u propart -f"
echo "3. Відкрийте в браузері: https://agent.pro-part.online"
echo ""
echo "🎉 Готово!"

