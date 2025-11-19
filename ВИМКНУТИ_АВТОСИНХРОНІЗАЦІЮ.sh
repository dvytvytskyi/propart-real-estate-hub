#!/bin/bash

echo "⚡ ВИМКНЕННЯ АВТОМАТИЧНОЇ СИНХРОНІЗАЦІЇ HUBSPOT"
echo "=========================================="
echo ""
echo "Це тимчасово вимкне автоматичну синхронізацію для покращення швидкості"
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# Створюємо резервну копію
if [ -f app.py ]; then
    cp app.py app.py.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Створено резервну копію app.py"
fi

# Коментуємо виклик start_background_sync()
echo "🔧 Вимкнення автоматичної синхронізації..."
sed -i 's/^\([[:space:]]*\)start_background_sync()/\1# ⚡ ВИМКНЕНО: start_background_sync()  # Тимчасово вимкнено для оптимізації/' app.py

if grep -q "# ⚡ ВИМКНЕНО: start_background_sync" app.py; then
    echo "✅ Автоматична синхронізація вимкнена"
else
    echo "⚠️  Не вдалося знайти start_background_sync() в app.py"
    echo "Перевірте вручну рядок ~5737"
fi

echo ""
echo "🔄 Перезапуск ProPart..."
sudo systemctl restart propart
sleep 5

echo ""
echo "📊 Статус:"
systemctl status propart --no-pager | head -10

echo ""
echo "✅ Готово!"
echo ""
echo "Для повторного ввімкнення:"
echo "1. Розкоментуйте рядок з start_background_sync()"
echo "2. sudo systemctl restart propart"

