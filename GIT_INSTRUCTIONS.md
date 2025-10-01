# 📝 Інструкції для завантаження на GitHub

## ✅ Git ініціалізовано локально!

Ваш проект готовий до завантаження на GitHub.

---

## 🚀 Варіант 1: Створити новий репозиторій на GitHub

### Крок 1: Створіть репозиторій на GitHub
1. Перейдіть на https://github.com/new
2. Назва репозиторію: `propart-real-estate-hub` (або ваша назва)
3. Опис: "Real Estate Lead Management System with HubSpot Integration"
4. **Приватний** або Публічний (рекомендую приватний)
5. **НЕ додавайте** README, .gitignore, або license (вони вже є)
6. Натисніть "Create repository"

### Крок 2: Підключіть remote та запуште
```bash
cd "/Users/vytvytskyi/Desktop/new project pro-part.hub"

# Додайте remote (замініть YOUR_USERNAME на ваш GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/propart-real-estate-hub.git

# Або якщо використовуєте SSH
git remote add origin git@github.com:YOUR_USERNAME/propart-real-estate-hub.git

# Перейменуйте branch на main (якщо потрібно)
git branch -M main

# Запуште код
git push -u origin main
```

---

## 🚀 Варіант 2: Використати GitHub CLI (швидше)

### Якщо встановлено GitHub CLI:
```bash
cd "/Users/vytvytskyi/Desktop/new project pro-part.hub"

# Аутентифікація (якщо ще не зробили)
gh auth login

# Створити репозиторій та запушити одразу
gh repo create propart-real-estate-hub --private --source=. --remote=origin --push
```

---

## 📋 Після завантаження

### Ваш репозиторій буде доступний за адресою:
```
https://github.com/YOUR_USERNAME/propart-real-estate-hub
```

### Клонування на сервер:
```bash
# На вашому сервері
git clone https://github.com/YOUR_USERNAME/propart-real-estate-hub.git /var/www/propart
cd /var/www/propart
sudo ./deploy.sh
```

---

## 🔐 Налаштування GitHub Secrets (для CI/CD)

Якщо плануєте автоматичний deploy:

1. Перейдіть в Settings → Secrets and variables → Actions
2. Додайте секрети:
   - `SERVER_HOST` - IP вашого сервера
   - `SERVER_USER` - SSH користувач
   - `SSH_PRIVATE_KEY` - ваш SSH ключ
   - `SECRET_KEY` - Flask secret key
   - `DATABASE_URL` - URL бази даних
   - `HUBSPOT_API_KEY` - HubSpot API ключ

---

## 📊 Що включено в репозиторій

✅ **50 файлів** успішно додано:
- ✅ Весь код застосунку
- ✅ Конфігураційні файли (gunicorn, nginx, systemd)
- ✅ Deploy скрипт
- ✅ Документація (README, deployment guides)
- ✅ .gitignore (не включає .env, логи, venv)

---

## 🚫 Що НЕ включено (захищено .gitignore)

- ❌ `.env` файл (credentials)
- ❌ `logs/` (логи)
- ❌ `venv/` (Python virtual environment)
- ❌ `__pycache__/` (Python cache)
- ❌ `*.pyc` (compiled Python)
- ❌ База даних файли

---

## 🔄 Майбутні оновлення

```bash
# Внести зміни в код
# ...

# Додати зміни
git add .

# Commit
git commit -m "Add new feature"

# Push
git push origin main

# На сервері оновити
ssh user@server
cd /var/www/propart
git pull origin main
sudo systemctl restart propart
```

---

## 📞 Що далі?

### 1. Створіть GitHub репозиторій
### 2. Запуште код (команди вище)
### 3. Дайте мені URL репозиторію
### 4. Я допоможу з deployment на сервер!

---

## 💡 Підказка

Якщо у вас є проблеми з аутентифікацією GitHub:

### HTTPS (простіше):
```bash
git remote add origin https://github.com/YOUR_USERNAME/repo.git
# При push попросить username та personal access token
```

### SSH (рекомендовано):
```bash
# Згенеруйте SSH ключ якщо його немає
ssh-keygen -t ed25519 -C "your_email@example.com"

# Додайте в GitHub: Settings → SSH and GPG keys → New SSH key
# Вставте вміст ~/.ssh/id_ed25519.pub

git remote add origin git@github.com:YOUR_USERNAME/repo.git
```

---

## ✅ Git статус

```bash
# Перевірити статус
git status

# Перевірити remote
git remote -v

# Перевірити останні commits
git log --oneline -5
```

**Ваш проект готовий до завантаження на GitHub!** 🎉

