# 🔧 Виправлення помилки 502 Bad Gateway

## 🎯 Швидке виправлення (рекомендовано)

### Варіант 1: Автоматичне виправлення (найшвидше)

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
sudo ./QUICK_FIX_502.sh
```

Цей скрипт автоматично:
- ✅ Зупинить старі процеси Gunicorn
- ✅ Перезапустить PostgreSQL, ProPart та Nginx
- ✅ Перевірить, чи все працює

**Час виконання:** ~30 секунд

---

### Варіант 2: Повна діагностика та виправлення

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
sudo ./DIAGNOSE_502.sh    # Спочатку діагностика
sudo ./FIX_502_ERROR.sh   # Потім виправлення
```

---

### Варіант 3: Ручне виправлення (якщо скрипти не працюють)

```bash
# 1. Зупинити всі процеси Gunicorn
sudo pkill -9 gunicorn

# 2. Перезапустити всі сервіси
sudo systemctl restart postgresql
sudo systemctl restart propart
sudo systemctl restart nginx

# 3. Перевірити статус
sudo systemctl status propart
sudo systemctl status nginx
```

---

## 🔍 Що таке помилка 502?

**502 Bad Gateway** означає, що Nginx не може підключитися до вашого додатку (Gunicorn на порту 8000).

### Типові причини:

1. **Gunicorn не запущений** ❌
   - Перевірка: `sudo systemctl status propart`
   - Виправлення: `sudo systemctl start propart`

2. **Gunicorn упав через помилку в коді** ❌
   - Перевірка: `sudo journalctl -u propart -n 50`
   - Виправлення: Виправити помилку та перезапустити

3. **PostgreSQL не працює** ❌
   - Перевірка: `sudo systemctl status postgresql`
   - Виправлення: `sudo systemctl restart postgresql`

4. **Порт 8000 зайнятий іншим процесом** ❌
   - Перевірка: `sudo netstat -tlnp | grep :8000`
   - Виправлення: `sudo pkill -9 gunicorn && sudo systemctl restart propart`

5. **Недостатньо пам'яті** ❌
   - Перевірка: `free -h`
   - Виправлення: Очистити кеш або зменшити кількість workers

---

## 📋 Корисні команди для діагностики

### Перевірка статусу сервісів
```bash
sudo systemctl status postgresql propart nginx
```

### Перегляд логів
```bash
# Логи ProPart (Gunicorn)
sudo journalctl -u propart -n 50 --no-pager
sudo tail -f /var/log/propart/gunicorn_error.log

# Логи Nginx
sudo tail -f /var/log/nginx/propart_error.log
sudo tail -f /var/log/nginx/error.log
```

### Перевірка порту 8000
```bash
sudo netstat -tlnp | grep :8000
# або
sudo ss -tlnp | grep :8000
```

### Тест HTTP запиту
```bash
curl -I http://localhost:8000/
```

### Перевірка конфігурації Nginx
```bash
sudo nginx -t
```

---

## 🚨 Якщо нічого не допомагає

### 1. Перевірте логи детально:
```bash
sudo journalctl -u propart -n 100 --no-pager > /tmp/propart_logs.txt
cat /tmp/propart_logs.txt
```

### 2. Перевірте права доступу:
```bash
ls -la /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/
ls -la /var/log/propart/
ls -la /var/run/propart/
```

### 3. Перевірте .env файл:
```bash
cat /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/.env
```

### 4. Перевірте конфігурацію systemd:
```bash
cat /etc/systemd/system/propart.service
sudo systemctl daemon-reload
sudo systemctl restart propart
```

---

## ✅ Після виправлення

1. Перевірте сайт у браузері:
   ```
   https://agent.pro-part.online
   ```

2. Якщо все працює:
   - ✅ Сторінка завантажується
   - ✅ Немає помилки 502
   - ✅ Можна залогінитися

3. Якщо досі є проблеми:
   - Запустіть повну діагностику: `sudo ./DIAGNOSE_502.sh`
   - Збережіть вивід та надішліть для аналізу

---

## 🔄 Профілактика

### Налаштувати автоматичний перезапуск при падінні:

Сервіс `propart` вже має `Restart=always` в конфігурації, тому автоматично перезапускається при падінні.

### Моніторинг (опціонально):

```bash
# Створити скрипт моніторингу
sudo nano /usr/local/bin/monitor_propart.sh
```

Додати:
```bash
#!/bin/bash
if ! systemctl is-active --quiet propart; then
    echo "$(date): ProPart down, restarting..." >> /var/log/propart_monitor.log
    systemctl restart propart
fi
```

Зробити виконуваним:
```bash
sudo chmod +x /usr/local/bin/monitor_propart.sh
```

Додати в cron (кожні 5 хвилин):
```bash
sudo crontab -e
# Додати:
*/5 * * * * /usr/local/bin/monitor_propart.sh
```

---

## 📞 Додаткова допомога

Якщо проблема не вирішується, надайте наступну інформацію:

```bash
# Зберегти всю діагностичну інформацію
sudo ./DIAGNOSE_502.sh > /tmp/diagnostic_502.txt 2>&1
sudo journalctl -u propart -n 100 --no-pager >> /tmp/diagnostic_502.txt
cat /tmp/diagnostic_502.txt
```

---

**Успіхів! 🚀**

