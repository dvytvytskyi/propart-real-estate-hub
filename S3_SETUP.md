# 📁 Налаштування AWS S3 для зберігання документів

## Що змінено

Система документів тепер використовує **AWS S3** замість локального зберігання файлів. Це забезпечує:
- ✅ Надійне хмарне зберігання
- ✅ Масштабованість
- ✅ Безпеку
- ✅ Резервне копіювання

## Необхідні змінні середовища

Додайте ці змінні до вашого `.env` файлу:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_S3_BUCKET=your_bucket_name
AWS_REGION=eu-central-1
```

## Як отримати AWSCredentialsCREDENTIALS

### 1. Створіть AWS акаунт
- Перейдіть на https://aws.amazon.com/
- Зареєструйтесь або увійдіть

### 2. Створіть S3 Bucket
1. Відкрийте AWS Console → S3
2. Натисніть **Create bucket**
3. Вкажіть унікальну назву (наприклад: `propart-documents`)
4. Виберіть регіон (рекомендовано: `eu-central-1` для Європи)
5. **Block Public Access**: залиште ВСІ галочки ✅ (bucket має бути приватним)
6. Натисніть **Create bucket**

### 3. Налаштуйте CORS (якщо потрібен доступ з браузера)
1. Виберіть ваш bucket
2. Перейдіть на вкладку **Permissions**
3. Прокрутіть до **Cross-origin resource sharing (CORS)**
4. Додайте:
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
    }
]
```

### 4. Створіть IAM користувача для програмного доступу
1. AWS Console → IAM → Users
2. Натисніть **Add users**
3. Вкажіть ім'я: `propart-s3-user`
4. Виберіть **Access key - Programmatic access**
5. Натисніть **Next: Permissions**
6. Виберіть **Attach existing policies directly**
7. Знайдіть і виберіть: `AmazonS3FullAccess` (або створіть власну політику з обмеженими правами)
8. Натисніть **Next** → **Create user**
9. **ВАЖЛИВО**: Збережіть **Access Key ID** та **Secret Access Key** (вони більше не будуть показані!)

### 5. Альтернативно: Політика з обмеженими правами (рекомендовано)
Замість `AmazonS3FullAccess` створіть власну політику:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name/*",
                "arn:aws:s3:::your-bucket-name"
            ]
        }
    ]
}
```

## Структура файлів в S3

Файли зберігаються за структурою:
```
user_documents/
  ├── {user_id}/
  │   ├── {uuid}.pdf
  │   ├── {uuid}.jpg
  │   └── {uuid}.docx
  └── ...
```

## Перевірка налаштування

1. Переконайтесь що всі змінні додані до `.env`
2. Перезапустіть сервер
3. Спробуйте завантажити документ через адмін-панель
4. Перевірте S3 bucket - файл має з'явитись там

## Підтримувані формати файлів

- 📄 PDF (`.pdf`)
- 📝 Word (`.doc`, `.docx`)
- 🖼️ Зображення (`.jpg`, `.jpeg`, `.png`)
- 📋 Текст (`.txt`)

**Максимальний розмір файлу**: 10 MB

## Вартість

AWS S3 має дуже низьку вартість:
- Зберігання: ~$0.023 за GB на місяць
- Запити GET: $0.0004 за 1000 запитів
- Запити PUT: $0.005 за 1000 запитів

Для малого/середнього проєкту це буде коштувати менше $1 на місяць.

## Troubleshooting

### Помилка: "S3 не налаштовано"
- Перевірте що всі змінні середовища встановлені
- Перезапустіть сервер після додавання змінних

### Помилка: "Access Denied"
- Перевірте IAM права користувача
- Переконайтесь що bucket існує і має правильну назву
- Перевірте що регіон вказано правильно

### Помилка: "Bucket does not exist"
- Перевірте назву bucket в `.env`
- Переконайтесь що bucket створено в правильному регіоні

## Міграція існуючих файлів

Якщо у вас вже є файли в локальній папці `uploads/user_documents/`, створіть скрипт для міграції:

```python
import os
import boto3
from app import app, db, UserDocument

def migrate_to_s3():
    s3_client = boto3.client('s3')
    bucket = app.config['AWS_S3_BUCKET']
    
    documents = UserDocument.query.all()
    for doc in documents:
        if os.path.exists(doc.file_path):
            # Завантажуємо файл в S3
            s3_path = f"user_documents/{doc.user_id}/{os.path.basename(doc.file_path)}"
            s3_client.upload_file(doc.file_path, bucket, s3_path)
            
            # Оновлюємо шлях в БД
            doc.file_path = s3_path
    
    db.session.commit()
    print("✅ Міграція завершена!")

if __name__ == '__main__':
    with app.app_context():
        migrate_to_s3()
```

## Безпека

- ✅ Bucket має бути **приватним** (Block Public Access увімкнено)
- ✅ Файли доступні тільки через Flask додаток з авторизацією
- ✅ IAM користувач має мінімальні необхідні права
- ✅ Access keys зберігаються в `.env` (не в git!)

