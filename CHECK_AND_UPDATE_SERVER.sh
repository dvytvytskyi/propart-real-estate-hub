#!/bin/bash

# Скрипт для перевірки та оновлення сервера
# IP: 188.245.228.175
# Користувач: pro-part-agent
# Директорія: /home/pro-part-agent/htdocs/agent.pro-part.online/

echo "🔍 === ПЕРЕВІРКА ТА ОНОВЛЕННЯ СЕРВЕРА ==="
echo ""
echo "IP сервера: 188.245.228.175"
echo "Користувач: pro-part-agent"
echo "Домен: agent.pro-part.online"
echo ""

# Команди для виконання на сервері:
echo "📋 Команди для SSH:"
echo ""
echo "1️⃣ Підключення:"
echo "   ssh pro-part-agent@188.245.228.175"
echo ""
echo "2️⃣ Перехід в директорію проекту:"
echo "   cd /home/pro-part-agent/htdocs/agent.pro-part.online/"
echo ""
echo "3️⃣ Перевірка поточного стану:"
echo "   git status"
echo "   git log --oneline -5"
echo ""
echo "4️⃣ Перевірка чи є нові зміни:"
echo "   git fetch origin"
echo "   git log HEAD..origin/main --oneline"
echo ""
echo "5️⃣ Оновлення коду:"
echo "   git pull origin main"
echo ""
echo "6️⃣ Перевірка .env файлу:"
echo "   cat .env | grep HUBSPOT"
echo ""
echo "7️⃣ Перевірка чи працює діагностичний ендпоінт (після оновлення):"
echo "   curl -s https://agent.pro-part.online/api/diagnostic | python3 -m json.tool"
echo ""
echo "8️⃣ Перезапуск додатка (залежить від налаштування CloudPanel):"
echo "   # Через CloudPanel UI: Python Settings → Restart Application"
echo "   # Або якщо через systemd:"
echo "   sudo systemctl restart propart"
echo ""
echo "9️⃣ Перевірка логів:"
echo "   tail -f /var/log/propart/app.log"
echo "   # або в CloudPanel: Application Logs"
echo ""

