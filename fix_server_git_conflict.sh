#!/bin/bash

echo "🔧 ВИПРАВЛЕННЯ КОНФЛІКТУ GIT НА СЕРВЕРІ"
echo "=========================================="
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# Перевірка статусу
echo "📊 Поточний статус git:"
git status --short
echo ""

# Збереження локальних змін (якщо потрібно буде відновити)
echo "💾 Збереження локальних змін у stash..."
git stash push -m "Локальні зміни перед pull $(date +%Y-%m-%d_%H:%M:%S)"
echo ""

# Оновлення з GitHub
echo "⬇️  Оновлення з GitHub..."
git pull origin main
echo ""

# Перевірка результату
if [ $? -eq 0 ]; then
    echo "✅ Успішно оновлено!"
    echo ""
    echo "📋 Останні зміни:"
    git log --oneline -3
    echo ""
    echo "🔄 Перезапуск сервісу..."
    sudo systemctl restart propart
    echo ""
    echo "✅ Готово! Зміни застосовано."
    echo ""
    echo "💡 Якщо потрібно відновити старі локальні зміни:"
    echo "   git stash list"
    echo "   git stash pop"
else
    echo "❌ Помилка при оновленні!"
    echo ""
    echo "Спробуйте вручну:"
    echo "   git stash"
    echo "   git pull origin main"
    echo "   sudo systemctl restart propart"
fi

