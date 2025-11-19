#!/bin/bash

echo "🔍 Перевірка помилок systemd service..."
echo ""

echo "1️⃣ Статус сервісу:"
sudo systemctl status propart --no-pager -l | head -30
echo ""

echo "2️⃣ Останні логи помилок:"
sudo journalctl -u propart -n 50 --no-pager | tail -30
echo ""

echo "3️⃣ Перевірка шляхів:"
echo "   WorkingDirectory:"
grep WorkingDirectory /etc/systemd/system/propart.service
echo "   ExecStart:"
grep ExecStart /etc/systemd/system/propart.service
echo ""

echo "4️⃣ Перевірка існування файлів:"
PROJECT_DIR="/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub"
echo "   Проект: $([ -d "$PROJECT_DIR" ] && echo '✅' || echo '❌') $PROJECT_DIR"
echo "   venv: $([ -d "$PROJECT_DIR/venv" ] && echo '✅' || echo '❌') $PROJECT_DIR/venv"
echo "   gunicorn_config.py: $([ -f "$PROJECT_DIR/gunicorn_config.py" ] && echo '✅' || echo '❌') $PROJECT_DIR/gunicorn_config.py"
echo "   run.py: $([ -f "$PROJECT_DIR/run.py" ] && echo '✅' || echo '❌') $PROJECT_DIR/run.py"
echo "   .env: $([ -f "$PROJECT_DIR/.env" ] && echo '✅' || echo '❌') $PROJECT_DIR/.env"
echo ""

echo "5️⃣ Перевірка gunicorn в venv:"
if [ -f "$PROJECT_DIR/venv/bin/gunicorn" ]; then
    echo "   ✅ Gunicorn знайдено"
    ls -la "$PROJECT_DIR/venv/bin/gunicorn"
else
    echo "   ❌ Gunicorn не знайдено!"
fi

