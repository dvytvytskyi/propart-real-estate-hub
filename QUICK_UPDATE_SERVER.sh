#!/bin/bash

echo "🚀 Швидке оновлення ProPart на сервері"
echo "========================================"

# Кольори для виводу
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Перевірка підключення до інтернету
echo -e "${BLUE}📡 Перевірка підключення...${NC}"
if ! ping -c 1 google.com &> /dev/null; then
    echo -e "${RED}❌ Немає підключення до інтернету${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Підключення OK${NC}"

# Git pull
echo -e "\n${BLUE}📥 Завантаження останніх змін з Git...${NC}"
git pull origin main
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Помилка при git pull${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Git pull завершено${NC}"

# Активація віртуального середовища
echo -e "\n${BLUE}🔧 Активація віртуального середовища...${NC}"
source venv/bin/activate
echo -e "${GREEN}✅ Віртуальне середовище активовано${NC}"

# Оновлення залежностей (якщо потрібно)
echo -e "\n${BLUE}📦 Перевірка залежностей...${NC}"
pip install -r requirements.txt --quiet
echo -e "${GREEN}✅ Залежності оновлено${NC}"

# Перезапуск сервісу
echo -e "\n${BLUE}🔄 Перезапуск Gunicorn...${NC}"
if command -v systemctl &> /dev/null; then
    # Якщо systemd доступний
    sudo systemctl restart propart
    sleep 3
    sudo systemctl status propart --no-pager
    echo -e "${GREEN}✅ Сервіс перезапущено через systemd${NC}"
else
    # Якщо systemd недоступний, використовуємо pkill
    pkill -f gunicorn
    sleep 2
    nohup gunicorn -c gunicorn_config.py wsgi:app > /dev/null 2>&1 &
    echo -e "${GREEN}✅ Gunicorn перезапущено${NC}"
fi

echo -e "\n${GREEN}🎉 Оновлення завершено!${NC}"
echo "========================================"
echo -e "Перевірте сайт: ${BLUE}https://agent.pro-part.online${NC}"

