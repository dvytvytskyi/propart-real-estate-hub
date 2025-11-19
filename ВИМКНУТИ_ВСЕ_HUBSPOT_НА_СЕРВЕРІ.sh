#!/bin/bash

echo "⚡ ПОВНЕ ВИМКНЕННЯ ВСІХ АВТОМАТИЧНИХ ВИКЛИКІВ HUBSPOT"
echo "=========================================="
echo "Це вимкне ВСІ автоматичні виклики HubSpot для максимальної швидкості"
echo ""

cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# Створюємо резервну копію
if [ -f app.py ]; then
    cp app.py app.py.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Створено резервну копію app.py"
fi

echo "🔧 Вимкнення автоматичної синхронізації..."

# 1. Вимкнути start_background_sync()
if grep -q "^[[:space:]]*start_background_sync()" app.py; then
    sed -i 's/^\([[:space:]]*\)start_background_sync()/\1# ⚡ ВИМКНЕНО: start_background_sync()  # Вимкнено для оптимізації/' app.py
    echo "✅ Вимкнено start_background_sync()"
else
    echo "ℹ️  start_background_sync() вже вимкнено або не знайдено"
fi

# 2. Перевірити чи є інші автоматичні виклики
echo ""
echo "🔍 Перевірка інших автоматичних викликів HubSpot..."

# Перевірка update_hubspot_stage_labels_for_leads в dashboard
if grep -A 2 "@app.route('/dashboard')" app.py | grep -E "update_hubspot_stage_labels_for_leads" | grep -v "^[[:space:]]*#"; then
    echo "⚠️  Знайдено активний виклик update_hubspot_stage_labels_for_leads в dashboard"
    echo "   Коментую..."
    sed -i '/update_hubspot_stage_labels_for_leads/s/^\([[:space:]]*\)\(updated_count = update_hubspot_stage_labels_for_leads\)/\1# ⚡ ВИМКНЕНО: \2/' app.py
    echo "✅ Вимкнено"
fi

# Перевірка sync_all_leads_from_hubspot в dashboard
if grep -A 5 "@app.route('/dashboard')" app.py | grep -E "sync_all_leads_from_hubspot" | grep -v "^[[:space:]]*#"; then
    echo "⚠️  Знайдено активний виклик sync_all_leads_from_hubspot в dashboard"
    echo "   Коментую..."
    sed -i '/sync_all_leads_from_hubspot/s/^\([[:space:]]*\)\(sync_all_leads_from_hubspot\)/\1# ⚡ ВИМКНЕНО: \2/' app.py
    echo "✅ Вимкнено"
fi

echo ""
echo "✅ Автоматичні виклики HubSpot вимкнено"
echo ""
echo "🔄 Перезапуск ProPart..."
sudo systemctl restart propart
sleep 5

echo ""
echo "📊 Статус:"
systemctl status propart --no-pager | head -15

echo ""
echo "🔍 Перевірка процесів:"
ps aux | grep -E "[g]unicorn" | head -3

echo ""
echo "✅ Готово!"
echo ""
echo "Тепер система працює БЕЗ автоматичних викликів HubSpot."
echo "Синхронізацію можна запускати вручну через кнопку в інтерфейсі."
echo ""
echo "Перевірте швидкість завантаження сторінок - має бути значно швидше!"

