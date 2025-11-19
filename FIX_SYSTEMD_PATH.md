# 🔧 Виправлення шляху systemd service

## ❌ Проблема

Systemd service використовував неправильний шлях:
- **Було:** `/var/www/propart`
- **Правильно:** `/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub`

Це означало, що сервіс запускався зі старого місця, а не з актуального коду в CloudPanel.

---

## ✅ Виправлення

Оновлено `propart.service` з правильними шляхами для CloudPanel.

---

## 📋 Команди для оновлення на сервері

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
git pull origin main
sudo cp propart.service /etc/systemd/system/propart.service
sudo systemctl daemon-reload
sudo systemctl restart propart
sudo systemctl status propart
```

---

## 🔍 Перевірка

Після оновлення перевірте, що сервіс використовує правильний шлях:

```bash
sudo systemctl status propart | grep -i "workingdirectory\|execstart"
```

Має показувати:
- `WorkingDirectory=/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub`
- `ExecStart=/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/venv/bin/gunicorn`

---

## 💡 Важливо

Після оновлення systemd service:
1. **Перезапустіть сервіс** - щоб він використовував новий код
2. **Перевірте логи** - щоб переконатися, що все працює правильно
3. **Додайте тестовий коментар** - щоб перевірити синхронізацію з HubSpot

---

## 🧪 Тестування

Після оновлення:

1. **Додайте новий коментар** до ліда з `hubspot_deal_id`
2. **Перевірте логи:**
   ```bash
   sudo journalctl -u propart -f | grep -i "note\|deal\|асоціація"
   ```
3. **Перевірте в HubSpot** - нотатка має з'явитися в deal

