#!/bin/bash

# ============================================================
# 🔄 WRAPPER ДЛЯ sync_lead_to_hubspot.py
# Автоматично активує venv та запускає скрипт
# ============================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Перевірка, чи існує venv
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Помилка: venv не знайдено!"
    echo "💡 Створіть venv: python3 -m venv venv"
    exit 1
fi

# Активуємо venv та запускаємо скрипт
source venv/bin/activate
python3 sync_lead_to_hubspot.py "$@"
EXIT_CODE=$?
deactivate

exit $EXIT_CODE

