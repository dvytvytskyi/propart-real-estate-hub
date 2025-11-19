# 🔧 Виправлення CSRF помилки

## ❌ Проблема
```
AttributeError: 'CSRFProtect' object has no attribute 'error_handler'
```

## ✅ Рішення

Виправлено застарілий API Flask-WTF. У новіших версіях `@csrf.error_handler` замінений на `@app.errorhandler(CSRFError)`.

---

## 📋 Команди для виконання на сервері

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub
git pull origin main
source venv/bin/activate
python3 check_comment_sync.py
python3 sync_lead_to_hubspot.py
deactivate
sudo systemctl restart propart
```

---

## 🚀 Одна команда (скопіюйте всю)

```bash
cd /home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub && git pull origin main && source venv/bin/activate && python3 check_comment_sync.py && python3 sync_lead_to_hubspot.py && deactivate && sudo systemctl restart propart
```

---

## ✅ Що було виправлено

1. Додано імпорт `CSRFError` з `flask_wtf.csrf`
2. Замінено `@csrf.error_handler` на `@app.errorhandler(CSRFError)`
3. Оновлено сигнатуру функції для роботи з новим API

Тепер код сумісний з новішими версіями Flask-WTF!

