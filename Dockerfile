FROM python:3.12-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файли залежностей
COPY requirements.txt .

# Встановлюємо Python залежності
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код додатку
COPY . .

# Створюємо директорію для логів
RUN mkdir -p logs

# Відкриваємо порт
EXPOSE 8090

# Команда запуску
CMD ["gunicorn", "--bind", "0.0.0.0:8090", "--workers", "1", "--timeout", "120", "--access-logfile", "logs/access.log", "--error-logfile", "logs/error.log", "--log-level", "debug", "wsgi:application"]
