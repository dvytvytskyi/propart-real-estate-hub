# 🐳 Docker Deployment Guide

## 🚀 Швидкий запуск через Docker

### 1. Підключіться до сервера
```bash
ssh pro-part-agent@your-server-ip
```

### 2. Клонуйте репозиторій
```bash
cd ~/htdocs
git clone https://github.com/dvytvytskyi/propart-real-estate-hub.git agent.pro-part.online
cd agent.pro-part.online
```

### 3. Встановіть Docker (якщо не встановлений)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### 4. Запустіть через Docker Compose
```bash
# Запуск з MySQL базою
docker-compose up -d

# Перевірте статус
docker-compose ps

# Перегляньте логи
docker-compose logs -f app
```

### 5. Створіть таблиці БД
```bash
# Виконайте setup.py в контейнері
docker-compose exec app python3 setup.py
```

### 6. Перевірте роботу
```bash
# Перевірте статус
curl -I http://localhost:8090

# Відкрийте сайт
# http://agent.pro-part.online
```

## 🔧 Корисні команди

```bash
# Зупинити контейнери
docker-compose down

# Перезапустити
docker-compose restart

# Переглянути логи
docker-compose logs app
docker-compose logs db

# Ввійти в контейнер
docker-compose exec app bash

# Оновити код
git pull origin main
docker-compose build
docker-compose up -d
```

## 📋 Переваги Docker

- ✅ Ізольоване середовище
- ✅ Автоматичне встановлення залежностей
- ✅ Легке оновлення
- ✅ Консистентність між середовищами
- ✅ Вбудована MySQL база
