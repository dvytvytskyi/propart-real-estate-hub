# Виправлення проблеми з DNS для HubSpot

## Проблема
Сервер не може підключитися до HubSpot API через проблеми з DNS:
```
Failed to resolve 'api.hubapi.com' ([Errno -3] Temporary failure in name resolution)
```

## Рішення

### Варіант 1: Виправлення DNS налаштувань

На сервері виконайте:

```bash
# 1. Перевірте поточні DNS налаштування
cat /etc/resolv.conf

# 2. Додайте публічні DNS сервери (якщо їх немає)
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# 3. Перевірте, чи працює DNS
ping -c 2 api.hubapi.com

# 4. Якщо працює, перезапустіть сервіс
sudo systemctl restart propart
```

### Варіант 2: Використання скрипта для синхронізації

Якщо DNS не можна виправити зараз, використайте скрипт для синхронізації пізніше:

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub

# Синхронізувати конкретний лід
venv/bin/python3 sync_lead_to_hubspot.py <lead_id>

# Або синхронізувати всі несинхронізовані ліди
venv/bin/python3 sync_unsynced_leads_to_hubspot.py
```

### Варіант 3: Додати в /etc/hosts (тимчасове рішення)

```bash
# Отримайте IP адресу api.hubapi.com з іншого місця
# Наприклад, з вашого локального комп'ютера:
nslookup api.hubapi.com

# Потім додайте в /etc/hosts на сервері:
echo "<IP_ADDRESS> api.hubapi.com" >> /etc/hosts
```

## Перевірка після виправлення

```bash
# Перевірте DNS
ping -c 2 api.hubapi.com

# Перевірте, чи працює синхронізація
tail -f logs/propart.log | grep -i hubspot
```

## Важливо

Ліди зберігаються локально навіть якщо синхронізація з HubSpot не вдається. Після виправлення DNS можна синхронізувати їх через скрипт.

