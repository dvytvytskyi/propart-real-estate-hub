from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, TextAreaField, SelectField, HiddenField, DecimalField, validators
from flask_wtf import FlaskForm as Form
from dotenv import load_dotenv
import traceback
import os
import time
import threading
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import boto3
from botocore.exceptions import ClientError
import io
from hubspot import HubSpot
from logging_config import setup_logging
from hubspot_rate_limiter import hubspot_rate_limiter
from timezone_utils import get_ukraine_time, utc_to_ukraine, format_ukraine_time, parse_hubspot_timestamp

# Завантажуємо змінні середовища
load_dotenv()

app = Flask(__name__)

# ===== ЧАСОВИЙ ПОЯС =====
# Налаштовуємо часовий пояс для України (UTC+3)
import os
os.environ['TZ'] = 'Europe/Kiev'
import time
time.tzset()

# Додаємо конфігурацію часового поясу для Flask
app.config['TIMEZONE'] = 'Europe/Kiev'

# ===== БЕЗПЕКА =====
# Перевіряємо наявність SECRET_KEY
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    app.logger.warning("SECRET_KEY не встановлено! Використовується тимчасовий ключ. Додайте SECRET_KEY в .env файл!")
app.config['SECRET_KEY'] = SECRET_KEY

# ===== БАЗА ДАНИХ =====
# Покращена конфігурація з connection pooling
# За замовчуванням використовуємо SQLite, якщо DATABASE_URL не задано
import pathlib
basedir = pathlib.Path(__file__).parent.absolute()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    f'sqlite:///{basedir}/instance/propart.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# AWS S3 Configuration
app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
app.config['AWS_S3_BUCKET'] = os.getenv('AWS_S3_BUCKET')
app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'eu-central-1')

# Налаштування engine options залежно від типу бази даних
database_uri = app.config['SQLALCHEMY_DATABASE_URI']
if database_uri.startswith('sqlite'):
    # Для SQLite використовуємо базові налаштування
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
    }
else:
    # Для PostgreSQL використовуємо повні налаштування з connection pooling
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'
        }
    }

db = SQLAlchemy(app)

# ===== ЛОГУВАННЯ =====
setup_logging(app)

# ===== БЕЗПЕКА: CSRF захист =====
csrf = CSRFProtect(app)
app.logger.info("✅ CSRF захист активовано")

# ===== БЕЗПЕКА: Rate Limiting =====
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ===== БЕЗПЕКА: Bcrypt для паролів =====
bcrypt = Bcrypt(app)

# ===== LOGIN MANAGER =====
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ===== JINJA2 ФІЛЬТРИ =====
@app.template_filter('ukraine_time')
def ukraine_time_filter(dt, format_str='%d %B %Y %H:%M'):
    """Фільтр для форматування часу в українському часовому поясі"""
    return format_ukraine_time(dt, format_str)

# ===== AWS S3 CLIENT =====
def get_s3_client():
    """Створює та повертає S3 клієнт"""
    app.logger.info("🔍 === ПЕРЕВІРКА КОНФІГУРАЦІЇ S3 ===")
    
    access_key = app.config.get('AWS_ACCESS_KEY_ID')
    secret_key = app.config.get('AWS_SECRET_ACCESS_KEY')
    bucket = app.config.get('AWS_S3_BUCKET')
    region = app.config.get('AWS_REGION', 'eu-central-1')
    
    app.logger.info(f"   AWS_ACCESS_KEY_ID: {'✅ встановлено' if access_key else '❌ відсутнє'}")
    app.logger.info(f"   AWS_SECRET_ACCESS_KEY: {'✅ встановлено' if secret_key else '❌ відсутнє'}")
    app.logger.info(f"   AWS_S3_BUCKET: {bucket if bucket else '❌ відсутнє'}")
    app.logger.info(f"   AWS_REGION: {region}")
    
    if not all([access_key, secret_key, bucket]):
        app.logger.warning("⚠️ S3 не налаштовано повністю - використовуємо локальне зберігання")
        app.logger.info("   Для налаштування S3 додайте в .env файл:")
        app.logger.info("   AWS_ACCESS_KEY_ID=your_access_key")
        app.logger.info("   AWS_SECRET_ACCESS_KEY=your_secret_key")
        app.logger.info("   AWS_S3_BUCKET=your_bucket_name")
        app.logger.info("   AWS_REGION=eu-central-1")
        return None
    
    try:
        app.logger.info("🚀 Створення S3 клієнта...")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # Тестуємо підключення
        app.logger.info("🧪 Тестування підключення до S3...")
        s3_client.head_bucket(Bucket=bucket)
        app.logger.info("✅ S3 клієнт створено та протестовано успішно")
        return s3_client
        
    except Exception as e:
        app.logger.error(f"❌ Помилка створення S3 клієнта: {type(e).__name__}: {str(e)}")
        app.logger.warning("⚠️ Використовуємо локальне зберігання")
        return None

def upload_file_to_s3(file, filename):
    """Завантажує файл в S3 bucket з fallback на локальне зберігання"""
    app.logger.info(f"📤 === ПОЧАТОК ЗАВАНТАЖЕННЯ ФАЙЛУ ===")
    app.logger.info(f"   Файл: {filename}")
    app.logger.info(f"   Тип файлу: {getattr(file, 'content_type', 'unknown')}")
    app.logger.info(f"   Розмір файлу: {getattr(file, 'content_length', 'unknown')} байт")
    
    # Перевіряємо налаштування S3
    s3_client = get_s3_client()
    if not s3_client:
        app.logger.warning("⚠️ S3 не налаштовано - використовуємо локальне зберігання")
        return upload_file_locally(file, filename)
    
    try:
        bucket = app.config['AWS_S3_BUCKET']
        content_type = file.content_type if hasattr(file, 'content_type') else 'application/octet-stream'
        
        app.logger.info(f"   S3 Bucket: {bucket}")
        app.logger.info(f"   Content-Type: {content_type}")
        app.logger.info(f"   AWS Region: {app.config.get('AWS_REGION', 'eu-central-1')}")
        
        # Повертаємо на початок файлу перед завантаженням
        file.seek(0)
        
        # Завантажуємо файл в S3
        app.logger.info("🚀 Завантаження файлу в S3...")
        s3_client.upload_fileobj(
            file,
            bucket,
            filename,
            ExtraArgs={
                'ContentType': content_type,
                'ACL': 'public-read'  # Робимо файл публічним
            }
        )
        
        # Формуємо URL файлу
        s3_url = f"https://{bucket}.s3.{app.config['AWS_REGION']}.amazonaws.com/{filename}"
        app.logger.info(f"✅ Файл успішно завантажено в S3: {s3_url}")
        return s3_url
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        app.logger.error(f"❌ AWS ClientError: {error_code} - {error_message}")
        app.logger.error(f"   Повний response: {e.response}")
        app.logger.warning("⚠️ Помилка S3 - використовуємо локальне зберігання")
        return upload_file_locally(file, filename)
    except Exception as e:
        app.logger.error(f"❌ Загальна помилка завантаження в S3: {type(e).__name__}: {str(e)}")
        app.logger.warning("⚠️ Помилка S3 - використовуємо локальне зберігання")
        return upload_file_locally(file, filename)


def upload_file_locally(file, filename):
    """Завантажує файл локально як fallback"""
    app.logger.info(f"💾 Завантаження файлу локально: {filename}")
    
    try:
        # Створюємо папку якщо не існує
        upload_dir = os.path.join(app.root_path, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Визначаємо підпапку за типом файлу
        if 'properties' in filename:
            subdir = 'properties'
        elif 'units' in filename:
            subdir = 'units'
        elif 'documents' in filename:
            subdir = 'documents'
        else:
            subdir = 'misc'
        
        full_dir = os.path.join(upload_dir, subdir)
        os.makedirs(full_dir, exist_ok=True)
        
        # Зберігаємо файл
        local_filename = os.path.basename(filename)  # Беремо тільки ім'я файлу
        file_path = os.path.join(full_dir, local_filename)
        
        # Перевіряємо тип файлу
        if hasattr(file, 'save'):
            # Flask FileStorage
            file.save(file_path)
        else:
            # BytesIO або інший тип
            with open(file_path, 'wb') as f:
                f.write(file.read())
        
        # Формуємо URL для локального файлу
        local_url = f"/static/uploads/{subdir}/{local_filename}"
        app.logger.info(f"✅ Файл збережено локально: {local_url}")
        return local_url
        
    except Exception as e:
        app.logger.error(f"❌ Помилка локального зберігання: {type(e).__name__}: {str(e)}")
        raise Exception(f"Не вдалося зберегти файл: {str(e)}")

def download_file_from_s3(filename):
    """Завантажує файл з S3 bucket"""
    s3_client = get_s3_client()
    if not s3_client:
        raise Exception("S3 не налаштовано")
    
    try:
        file_obj = io.BytesIO()
        s3_client.download_fileobj(app.config['AWS_S3_BUCKET'], filename, file_obj)
        file_obj.seek(0)
        return file_obj
    except ClientError as e:
        app.logger.error(f"Помилка завантаження з S3: {e}")
        raise Exception(f"Не вдалося завантажити файл з S3: {str(e)}")

def delete_file_from_s3(filename):
    """Видаляє файл з S3 bucket або локально"""
    app.logger.info(f"🗑️ Видалення файлу: {filename}")
    
    # Перевіряємо, чи це локальний файл
    if filename.startswith('/static/uploads/'):
        return delete_file_locally(filename)
    
    # Спробуємо видалити з S3
    s3_client = get_s3_client()
    if not s3_client:
        app.logger.warning("⚠️ S3 не налаштовано - пропускаємо видалення з S3")
        return True
    
    try:
        s3_client.delete_object(Bucket=app.config['AWS_S3_BUCKET'], Key=filename)
        app.logger.info(f"✅ Файл видалено з S3: {filename}")
        return True
    except ClientError as e:
        app.logger.error(f"❌ Помилка видалення з S3: {e}")
        return False


def delete_file_locally(filename):
    """Видаляє локальний файл"""
    try:
        # Видаляємо /static/ з початку шляху
        if filename.startswith('/static/'):
            filename = filename[8:]  # Видаляємо '/static/'
        
        file_path = os.path.join(app.root_path, 'static', filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            app.logger.info(f"✅ Локальний файл видалено: {file_path}")
            return True
        else:
            app.logger.warning(f"⚠️ Локальний файл не знайдено: {file_path}")
            return True  # Не вважаємо це помилкою
    except Exception as e:
        app.logger.error(f"❌ Помилка видалення локального файлу: {e}")
        return False

# ===== HUBSPOT API =====
HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')
if HUBSPOT_API_KEY:
    try:
        hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
        app.logger.info("HubSpot API успішно підключено!")
        print("HubSpot API успішно підключено!")
    except Exception as e:
        app.logger.error(f"Помилка підключення HubSpot API: {e}")
        print(f"Помилка підключення HubSpot API: {e}")
        hubspot_client = None
else:
    app.logger.warning("HUBSPOT_API_KEY не знайдено в змінних середовища")
    print("HUBSPOT_API_KEY не знайдено в змінних середовища")
    hubspot_client = None

# Моделі бази даних
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')  # 'agent' або 'admin'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Прив'язка брокера до адміна
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # ID адміна для брокерів
    
    # Комісія агента (у відсотках)
    commission = db.Column(db.Float, default=0.0)
    
    # Геймифікація
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.String(20), default='bronze')  # bronze, silver, gold, platinum
    total_leads = db.Column(db.Integer, default=0)
    closed_deals = db.Column(db.Integer, default=0)
    
    # Верифікація
    is_verified = db.Column(db.Boolean, default=False)
    verification_requested = db.Column(db.Boolean, default=False)
    verification_request_date = db.Column(db.DateTime)
    verification_document_path = db.Column(db.String(200))
    verification_notes = db.Column(db.Text)
    
    # Статус акаунту
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Relationships
    # Брокери, які прив'язані до цього адміна
    brokers = db.relationship('User', backref=db.backref('admin', remote_side=[id]), lazy='dynamic', foreign_keys=[admin_id])
    
    def set_password(self, password):
        """Встановлює пароль з використанням bcrypt"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Перевіряє пароль (сумісність з Werkzeug та bcrypt)"""
        # Перевіряємо чи це старий Werkzeug hash
        if self.password_hash.startswith('pbkdf2:sha256'):
            from werkzeug.security import check_password_hash
            return check_password_hash(self.password_hash, password)
        # Інакше використовуємо bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def add_points(self, points):
        """Додає поінти та оновлює рівень"""
        self.points += points
        self.update_level()
    
    def update_level(self):
        """Оновлює рівень на основі поінтів"""
        if self.points >= 10000:
            self.level = 'platinum'
        elif self.points >= 5000:
            self.level = 'gold'
        elif self.points >= 2000:
            self.level = 'silver'
        else:
            self.level = 'bronze'
    
    def get_commission_rate(self):
        """Повертає відсоток комісії на основі рівня"""
        rates = {
            'bronze': 5,
            'silver': 7,
            'gold': 10,
            'platinum': 15
        }
        return rates.get(self.level, 5)
    
    def get_level_display_name(self):
        """Повертає відображуване ім'я рівня"""
        names = {
            'bronze': 'Бронзовий',
            'silver': 'Срібний', 
            'gold': 'Золотий',
            'platinum': 'Платиновий'
        }
        return names.get(self.level, 'Бронзовий')
    
    def is_account_locked(self):
        """Перевіряє, чи заблокований акаунт"""
        if self.locked_until:
            from datetime import datetime
            return datetime.now() < self.locked_until
        return False
    
    def lock_account(self, minutes=30):
        """Блокує акаунт на вказану кількість хвилин"""
        from datetime import datetime, timedelta
        self.locked_until = datetime.now() + timedelta(minutes=minutes)
        self.login_attempts = 0
    
    def unlock_account(self):
        """Розблоковує акаунт"""
        self.locked_until = None
        self.login_attempts = 0
    
    def increment_login_attempts(self):
        """Збільшує лічильник невдалих спроб входу"""
        self.login_attempts += 1
        if self.login_attempts >= 5:  # Блокуємо після 5 невдалих спроб
            self.lock_account()
    
    def reset_login_attempts(self):
        """Скидає лічильник невдалих спроб"""
        self.login_attempts = 0
        self.locked_until = None

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    agent = db.relationship('User', backref='leads', foreign_keys=[agent_id])
    deal_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    budget = db.Column(db.String(50))
    status = db.Column(db.String(50), default='new')
    is_transferred = db.Column(db.Boolean, default=False)  # Чи передано лід
    notes = db.Column(db.Text)
    last_updated_hubspot = db.Column(db.DateTime)  # Останній раз оновлювався в HubSpot
    
    # Додаткові поля
    country = db.Column(db.String(50))  # Країна покупки
    purchase_goal = db.Column(db.String(50))  # Мета покупки
    property_type = db.Column(db.String(50))  # Тип нерухомості
    object_type = db.Column(db.String(50))  # Тип об'єкта
    communication_language = db.Column(db.String(50))  # Мова спілкування
    source = db.Column(db.String(50))  # Джерело привернення
    refusal_reason = db.Column(db.String(50))  # Причина відмови
    
    # Контактні дані
    company = db.Column(db.String(100))  # Компанія
    second_phone = db.Column(db.String(20))  # Другий телефон
    telegram_nickname = db.Column(db.String(50))  # Нік в телеграмі
    messenger = db.Column(db.String(20))  # Месенджер
    birth_date = db.Column(db.Date)  # Дата народження
    
    hubspot_contact_id = db.Column(db.String(50))
    hubspot_deal_id = db.Column(db.String(50))
    hubspot_stage_label = db.Column(db.String(100))  # Оригінальна назва стадії з HubSpot
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    last_sync_at = db.Column(db.DateTime)  # Час останньої синхронізації з HubSpot


class Comment(db.Model):
    """Модель коментарів/нотаток для лідів (threaded comments)"""
    __tablename__ = 'comment'
    
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)  # Для threaded comments
    content = db.Column(db.Text, nullable=False)  # Текст коментаря
    hubspot_note_id = db.Column(db.String(50))  # ID нотатки в HubSpot
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Зв'язки
    lead = db.relationship('Lead', backref='comments')
    user = db.relationship('User', backref='comments')
    parent = db.relationship('Comment', remote_side=[id], backref='replies')
    
    def to_dict(self):
        """Конвертує коментар в словник для JSON"""
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else 'Unknown',
            'parent_id': self.parent_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'replies_count': len(self.replies) if self.replies else 0
        }


# Форми
class LoginForm(Form):
    username = StringField('Ім\'я користувача', [validators.Length(min=4, max=25)])
    password = PasswordField('Пароль', [validators.DataRequired()])

class LeadForm(Form):
    deal_name = StringField('Deal name', [validators.DataRequired(), validators.Length(min=2, max=100)])
    email = StringField('Email', [validators.Optional(), validators.Email()])
    phone = StringField('Phone number', [validators.DataRequired(), validators.Length(max=20)])
    second_phone = StringField('Другий номер телефону', [validators.Length(max=20)])
    company = StringField('Компанія', [validators.Length(max=100)])
    telegram_nickname = StringField('Telegram', [validators.Length(max=50)])
    messenger = StringField('Месенджер', [validators.Length(max=20)])
    birth_date = StringField('Дата народження')
    budget = SelectField('Budget', choices=[
        ('до 200к', 'до 200к'),
        ('200к–500к', '200к–500к'),
        ('500к–1млн', '500к–1млн'),
        ('1млн+', '1млн+')
    ], validators=[validators.DataRequired()])
    notes = TextAreaField('Примітки', [validators.Length(max=500)])
    agent_id = SelectField('Відповідальний агент', coerce=int, validators=[validators.DataRequired()])

class NoteForm(Form):
    note_text = TextAreaField('Нотатка', [validators.DataRequired(), validators.Length(min=1, max=1000)])

class RegistrationForm(Form):
    username = StringField('Ім\'я користувача', [validators.DataRequired(), validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Пароль', [validators.DataRequired(), validators.Length(min=6)])
    confirm_password = PasswordField('Підтвердіть пароль', [validators.DataRequired()])
    admin_id = SelectField('Адмін', coerce=int)
    
    def validate_username(self, field):
        """Валідація імені користувача"""
        username = field.data
        
        # Замінюємо пробіли на підкреслення
        username = username.replace(' ', '_')
        field.data = username
        
        # Перевіряємо на великі літери
        if any(c.isupper() for c in username):
            raise validators.ValidationError('Ім\'я користувача не може містити великі літери')
        
        # Перевіряємо на дозволені символи (тільки маленькі літери, цифри, підкреслення)
        import re
        if not re.match(r'^[a-z0-9_]+$', username):
            raise validators.ValidationError('Ім\'я користувача може містити тільки маленькі літери, цифри та підкреслення')
        
        # Перевіряємо, що не починається з цифри
        if username[0].isdigit():
            raise validators.ValidationError('Ім\'я користувача не може починатися з цифри')

class UserEditForm(Form):
    username = StringField('Ім\'я користувача', [validators.DataRequired(), validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    role = SelectField('Роль', choices=[
        ('agent', 'Агент'),
        ('admin', 'Адміністратор')
    ], validators=[validators.DataRequired()])
    is_active = SelectField('Статус', choices=[
        (True, 'Активний'),
        (False, 'Деактивований')
    ], coerce=bool)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    hubspot_activity_id = db.Column(db.String(50), unique=True)  # ID активності в HubSpot
    activity_type = db.Column(db.String(20), nullable=False)  # email, call, task, meeting, note
    subject = db.Column(db.String(200))  # Тема/назва активності
    body = db.Column(db.Text)  # Тіло/опис активності
    status = db.Column(db.String(20), default='completed')  # completed, pending, cancelled
    direction = db.Column(db.String(10))  # inbound, outbound (для calls, emails)
    duration = db.Column(db.Integer)  # Тривалість в секундах (для calls, meetings)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Зв'язок з лідом
    lead = db.relationship('Lead', backref='activities')

class UserDocument(db.Model):
    """Документи користувачів (паспорти, договори, тощо)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # Оригінальна назва файлу
    file_path = db.Column(db.String(500), nullable=False)  # Шлях до файлу на сервері
    file_size = db.Column(db.Integer)  # Розмір файлу в байтах
    file_type = db.Column(db.String(100))  # MIME type (image/jpeg, application/pdf, тощо)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Хто завантажив (адмін або сам користувач)
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    description = db.Column(db.String(500))  # Опис документу
    
    # Зв'язки
    user = db.relationship('User', foreign_keys=[user_id], backref='documents')
    uploader = db.relationship('User', foreign_keys=[uploaded_by])


class Property(db.Model):
    """Модель нерухомості"""
    __tablename__ = 'property'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Назва проекту
    location_country = db.Column(db.String(100), nullable=False)  # Країна
    location_city = db.Column(db.String(100), nullable=False)  # Місто
    location_district = db.Column(db.String(100))  # Район (опціонально)
    price_from = db.Column(db.Numeric(15, 2), nullable=False)  # Ціна від
    price_to = db.Column(db.Numeric(15, 2))  # Ціна до (опціонально)
    description = db.Column(db.Text)  # Опис проекту
    payment_type = db.Column(db.Text)  # Тип платежу (розтермінування)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Хто створив
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Зв'язки
    creator = db.relationship('User', backref='created_properties')
    photos = db.relationship('PropertyPhoto', backref='property', cascade='all, delete-orphan')
    units = db.relationship('PropertyUnit', backref='property', cascade='all, delete-orphan')
    documents = db.relationship('PropertyDocument', backref='property', cascade='all, delete-orphan')


class PropertyPhoto(db.Model):
    """Фото нерухомості"""
    __tablename__ = 'property_photo'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_main = db.Column(db.Boolean, default=False)  # Головне фото


class PropertyUnit(db.Model):
    """Планування квартир/юнітів"""
    __tablename__ = 'property_unit'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    unit_type = db.Column(db.String(50), nullable=False)  # studio, 1, 2, 3, 4, 5, 6
    size_from = db.Column(db.Numeric(8, 2), nullable=False)  # Розмір від
    size_to = db.Column(db.Numeric(8, 2))  # Розмір до (опціонально)
    price_per_unit = db.Column(db.Numeric(15, 2), nullable=False)  # Ціна за юніт
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Зв'язки
    photos = db.relationship('UnitPhoto', backref='unit', cascade='all, delete-orphan')


class UnitPhoto(db.Model):
    """Фото планування"""
    __tablename__ = 'unit_photo'
    
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('property_unit.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())


class PropertyDocument(db.Model):
    """Документи проекту (максимум 5)"""
    __tablename__ = 'property_document'
    
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    description = db.Column(db.String(500))  # Опис документу

class LeadEditForm(Form):
    deal_name = StringField('Deal name', [validators.DataRequired(), validators.Length(min=2, max=100)])
    email = StringField('Email', [validators.Optional(), validators.Email()])
    phone = StringField('Phone number', [validators.DataRequired(), validators.Length(max=20)])


class PropertyForm(Form):
    name = StringField('Назва проекту', [validators.DataRequired(), validators.Length(min=2, max=200)])
    location_country = SelectField('Країна', [validators.DataRequired()], choices=[
        ('Україна', 'Україна'),
        ('Дубай', 'Дубай'),
        ('Румунія', 'Румунія'),
        ('Занзибар', 'Занзибар'),
        ('Північний Кіпр', 'Північний Кіпр'),
        ('Південний Кіпр', 'Південний Кіпр'),
        ('Турція', 'Турція'),
        ('Балі', 'Балі'),
        ('Чорногорія', 'Чорногорія'),
        ('Болгарія', 'Болгарія'),
        ('Іспанія', 'Іспанія'),
        ('Інше', 'Інше')
    ])
    location_city = StringField('Місто', [validators.DataRequired(), validators.Length(min=2, max=100)])
    location_district = StringField('Район (опціонально)', [validators.Length(max=100)])
    price_from = DecimalField('Ціна від', [validators.DataRequired(), validators.NumberRange(min=0)])
    price_to = DecimalField('Ціна до (опціонально)', [validators.NumberRange(min=0)])
    description = TextAreaField('Опис проекту', [validators.Length(max=2000)], render_kw={'rows': 5})
    payment_type = TextAreaField('Тип платежу (розтермінування)', [validators.Length(max=1000)])


class UnitForm(Form):
    unit_type = SelectField('Тип планування', [validators.DataRequired()], choices=[
        ('studio', 'Studio'),
        ('1', '1 кімната'),
        ('2', '2 кімнати'),
        ('3', '3 кімнати'),
        ('4', '4 кімнати'),
        ('5', '5 кімнат'),
        ('6', '6 кімнат')
    ])
    size_from = DecimalField('Розмір від (м²)', [validators.DataRequired(), validators.NumberRange(min=0)])
    size_to = DecimalField('Розмір до (м²) (опціонально)', [validators.NumberRange(min=0)])
    price_per_unit = DecimalField('Ціна за юніт', [validators.DataRequired(), validators.NumberRange(min=0)])
    budget = SelectField('Budget', choices=[
        ('', 'Оберіть бюджет'),
        ('до 200к', 'до 200к'),
        ('200к–500к', '200к–500к'),
        ('500к–1млн', '500к–1млн'),
        ('1млн+', '1млн+')
    ])
    status = SelectField('Status', choices=[
        ('new', 'Нова заявка'),
        ('contacted', 'На зв\'язку'),
        ('qualified', 'Кваліфікований'),
        ('closed', 'Закритий')
    ])
    country = SelectField('Країна покупки', choices=[
        ('', 'Оберіть країну'),
        ('Дубай', 'Дубай'),
        ('Турція', 'Турція'),
        ('Балі', 'Балі'),
        ('Таїланд', 'Таїланд'),
        ('Камбоджа', 'Камбоджа'),
        ('Оман', 'Оман'),
        ('Абу-Дабі', 'Абу-Дабі'),
        ('Мальдіви', 'Мальдіви'),
        ('Румунія', 'Румунія'),
        ('Іспанія', 'Іспанія'),
        ('Чорногорія', 'Чорногорія'),
        ('Греція', 'Греція'),
        ('Північний Кіпр', 'Північний Кіпр'),
        ('Південний Кіпр', 'Південний Кіпр')
    ])
    purchase_goal = SelectField('Мета покупки', choices=[
        ('', 'Оберіть мету'),
        ('перепродажа', 'Перепродажа'),
        ('под аренду', 'Під аренду'),
        ('для себя', 'Для себе')
    ])
    property_type = SelectField('Тип нерухомості', choices=[
        ('', 'Оберіть тип'),
        ('офф-план', 'Офф-план'),
        ('вторичка', 'Вторичка'),
        ('коммерция', 'Комерція')
    ])
    object_type = SelectField('Тип об\'єкта', choices=[
        ('', 'Оберіть тип об\'єкта'),
        ('апартаменты', 'Апартаменти'),
        ('вилла', 'Вілла'),
        ('таунхаус', 'Таунхаус'),
        ('отельный номер', 'Готельний номер'),
        ('отель', 'Готель'),
        ('коммерческое помещение', 'Комерційне приміщення'),
        ('земля', 'Земля')
    ])
    communication_language = SelectField('Мова спілкування', choices=[
        ('', 'Оберіть мову'),
        ('украинский', 'Українська'),
        ('русский', 'Російська'),
        ('английский', 'Англійська')
    ])
    source = SelectField('Джерело привернення', choices=[
        ('', 'Оберіть джерело'),
        ('блогер-агент', 'Блогер-агент'),
        ('агент', 'Агент'),
        ('ютуб', 'YouTube'),
        ('соц сети компании', 'Соц мережі компанії'),
        ('соц сети Логачева', 'Соц мережі Логачова'),
        ('сайт', 'Сайт'),
        ('рекомендация', 'Рекомендація'),
        ('личный контакт', 'Особистий контакт'),
        ('реклама/таргет', 'Реклама/таргет')
    ])
    refusal_reason = SelectField('Причина відмови', choices=[
        ('', 'Оберіть причину'),
        ('игнорирует звонки и смс', 'Ігнорує дзвінки та SMS'),
        ('недостаточный бюджет', 'Недостатній бюджет'),
        ('не планирует покупать', 'Не планує купувати'),
        ('купил сам или с другим АН', 'Купив сам або з іншим АН'),
        ('не оставлял заявку', 'Не залишав заявку'),
        ('риелтор', 'Рієлтор'),
        ('менеджер застройщика', 'Менеджер забудовника')
    ])
    
    # Контактні дані
    company = StringField('Компанія', [validators.Length(max=100)])
    second_phone = StringField('Другий номер телефону', [validators.Length(max=20)])
    telegram_nickname = StringField('Нік в телеграмі', [validators.Length(max=50)])
    messenger = SelectField('Месенджер', choices=[
        ('', 'Оберіть месенджер'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('viber', 'Viber'),
        ('botim', 'Botim'),
        ('signal', 'Signal')
    ])
    birth_date = StringField('Дата народження', [validators.Length(max=10)])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_budget_value(budget_str):
    """Конвертує строку бюджету в числове значення для підрахунку"""
    if not budget_str:
        return 0
    
    budget_str = budget_str.lower().replace(' ', '')
    
    if 'до 200к' in budget_str:
        return 200000
    elif '200к–500к' in budget_str or '200к-500к' in budget_str:
        return 350000  # Середнє значення
    elif '500к–1млн' in budget_str or '500к-1млн' in budget_str:
        return 750000  # Середнє значення
    elif '1млн+' in budget_str:
        return 1500000  # Приблизне значення
    else:
        return 0

def fetch_activities_from_hubspot(lead):
    """Отримує активності з HubSpot для контакту та угоди"""
    if not hubspot_client or not lead.hubspot_contact_id:
        print(f"Немає HubSpot клієнта або ID контакту для ліда {lead.id}")
        return []
    
    activities = []
    
    try:
        # Отримуємо emails
        try:
            from hubspot.crm.objects.emails import PublicObjectSearchRequest
            from hubspot.crm.objects.emails import Filter, FilterGroup
            
            email_search_request = PublicObjectSearchRequest(
                filter_groups=[
                    FilterGroup(
                        filters=[
                            Filter(
                                property_name="hs_email_subject",
                                operator="HAS_PROPERTY"
                            )
                        ]
                    )
                ],
                properties=["hs_email_subject", "hs_email_text", "hs_email_direction", "hs_email_status", "hs_createdate"],
                limit=50
            )
            
            email_results = hubspot_client.crm.objects.emails.search_api.do_search(
                public_object_search_request=email_search_request
            )
            
            if email_results.results:
                for email in email_results.results:
                    if email.properties:
                        activities.append({
                            'id': str(email.id),
                            'type': 'email',
                            'subject': email.properties.get('hs_email_subject', ''),
                            'body': email.properties.get('hs_email_text', ''),
                            'direction': email.properties.get('hs_email_direction', ''),
                            'status': email.properties.get('hs_email_status', ''),
                            'createdate': email.properties.get('hs_createdate'),
                            'source': 'email'
                        })
        except Exception as email_error:
            print(f"Помилка отримання emails: {email_error}")
        
        # Отримуємо calls
        try:
            from hubspot.crm.objects.calls import PublicObjectSearchRequest
            from hubspot.crm.objects.calls import Filter, FilterGroup
            
            call_search_request = PublicObjectSearchRequest(
                filter_groups=[
                    FilterGroup(
                        filters=[
                            Filter(
                                property_name="hs_call_title",
                                operator="HAS_PROPERTY"
                            )
                        ]
                    )
                ],
                properties=["hs_call_title", "hs_call_body", "hs_call_direction", "hs_call_status", "hs_call_duration", "hs_createdate"],
                limit=50
            )
            
            call_results = hubspot_client.crm.objects.calls.search_api.do_search(
                public_object_search_request=call_search_request
            )
            
            if call_results.results:
                for call in call_results.results:
                    if call.properties:
                        activities.append({
                            'id': str(call.id),
                            'type': 'call',
                            'subject': call.properties.get('hs_call_title', ''),
                            'body': call.properties.get('hs_call_body', ''),
                            'direction': call.properties.get('hs_call_direction', ''),
                            'status': call.properties.get('hs_call_status', ''),
                            'duration': call.properties.get('hs_call_duration'),
                            'createdate': call.properties.get('hs_createdate'),
                            'source': 'call'
                        })
        except Exception as call_error:
            print(f"Помилка отримання calls: {call_error}")
        
        # Отримуємо tasks
        try:
            from hubspot.crm.objects.tasks import PublicObjectSearchRequest
            from hubspot.crm.objects.tasks import Filter, FilterGroup
            
            task_search_request = PublicObjectSearchRequest(
                filter_groups=[
                    FilterGroup(
                        filters=[
                            Filter(
                                property_name="hs_task_subject",
                                operator="HAS_PROPERTY"
                            )
                        ]
                    )
                ],
                properties=["hs_task_subject", "hs_task_body", "hs_task_status", "hs_createdate"],
                limit=50
            )
            
            task_results = hubspot_client.crm.objects.tasks.search_api.do_search(
                public_object_search_request=task_search_request
            )
            
            if task_results.results:
                for task in task_results.results:
                    if task.properties:
                        activities.append({
                            'id': str(task.id),
                            'type': 'task',
                            'subject': task.properties.get('hs_task_subject', ''),
                            'body': task.properties.get('hs_task_body', ''),
                            'status': task.properties.get('hs_task_status', ''),
                            'createdate': task.properties.get('hs_createdate'),
                            'source': 'task'
                        })
        except Exception as task_error:
            print(f"Помилка отримання tasks: {task_error}")
        
        # Отримуємо meetings
        try:
            from hubspot.crm.objects.meetings import PublicObjectSearchRequest
            from hubspot.crm.objects.meetings import Filter, FilterGroup
            
            meeting_search_request = PublicObjectSearchRequest(
                filter_groups=[
                    FilterGroup(
                        filters=[
                            Filter(
                                property_name="hs_meeting_title",
                                operator="HAS_PROPERTY"
                            )
                        ]
                    )
                ],
                properties=["hs_meeting_title", "hs_meeting_body", "hs_meeting_status", "hs_meeting_duration", "hs_createdate"],
                limit=50
            )
            
            meeting_results = hubspot_client.crm.objects.meetings.search_api.do_search(
                public_object_search_request=meeting_search_request
            )
            
            if meeting_results.results:
                for meeting in meeting_results.results:
                    if meeting.properties:
                        activities.append({
                            'id': str(meeting.id),
                            'type': 'meeting',
                            'subject': meeting.properties.get('hs_meeting_title', ''),
                            'body': meeting.properties.get('hs_meeting_body', ''),
                            'status': meeting.properties.get('hs_meeting_status', ''),
                            'duration': meeting.properties.get('hs_meeting_duration'),
                            'createdate': meeting.properties.get('hs_createdate'),
                            'source': 'meeting'
                        })
        except Exception as meeting_error:
            print(f"Помилка отримання meetings: {meeting_error}")
        
        print(f"Отримано {len(activities)} активностей з HubSpot для ліда {lead.id}")
        return activities
        
    except Exception as e:
        print(f"Помилка отримання активностей з HubSpot для ліда {lead.id}: {e}")
        return []

def sync_activities_from_hubspot(lead):
    """Синхронізує активності з HubSpot в локальну БД"""
    if not hubspot_client or not lead.hubspot_contact_id:
        return False
    
    try:
        # Отримуємо активності з HubSpot
        hubspot_activities = fetch_activities_from_hubspot(lead)
        
        for activity_data in hubspot_activities:
            # Перевіряємо, чи існує вже така активність в локальній БД
            existing_activity = Activity.query.filter_by(
                hubspot_activity_id=activity_data['id']
            ).first()
            
            if not existing_activity and activity_data['subject'].strip():
                # Створюємо нову активність в локальній БД
                new_activity = Activity(
                    lead_id=lead.id,
                    hubspot_activity_id=activity_data['id'],
                    activity_type=activity_data['type'],
                    subject=activity_data['subject'],
                    body=activity_data.get('body', ''),
                    status=activity_data.get('status', 'completed'),
                    direction=activity_data.get('direction', ''),
                    duration=activity_data.get('duration')
                )
                
                # Встановлюємо дату створення з HubSpot, якщо є
                if activity_data.get('createdate'):
                    try:
                        # HubSpot дата в форматі timestamp (мілісекунди)
                        timestamp_ms = int(activity_data['createdate'])
                        new_activity.created_at = parse_hubspot_timestamp(timestamp_ms)
                    except (ValueError, TypeError):
                        pass  # Використовуємо поточну дату
                
                db.session.add(new_activity)
                print(f"Додано активність з HubSpot для ліда {lead.id}: {activity_data['type']} - {activity_data['subject'][:50]}...")
        
        db.session.commit()
        print(f"Синхронізовано {len(hubspot_activities)} активностей з HubSpot для ліда {lead.id}")
        return True
        
    except Exception as e:
        print(f"Помилка синхронізації активностей для ліда {lead.id}: {e}")
        db.session.rollback()
        return False

def update_hubspot_owner(lead, new_agent_id):
    """Оновлює hubspot_owner_id в HubSpot угоді при зміні агента"""
    if not hubspot_client or not lead.hubspot_deal_id:
        return False
    
    try:
        # Отримуємо нового агента
        new_agent = User.query.get(new_agent_id)
        if not new_agent:
            print(f"⚠️ Агент з ID {new_agent_id} не знайдено")
            return False
        
        # Шукаємо HubSpot owner ID для нового агента
        hubspot_owner_id = None
        try:
            print(f"🔍 Пошук HubSpot owner для нового агента: {new_agent.email}")
            owners = hubspot_client.crm.owners.owners_api.get_page()
            for owner in owners.results:
                if owner.email and owner.email.lower() == new_agent.email.lower():
                    hubspot_owner_id = str(owner.id)
                    print(f"✅ Знайдено HubSpot owner ID: {hubspot_owner_id} для {new_agent.email}")
                    break
            if not hubspot_owner_id:
                print(f"⚠️ HubSpot owner не знайдено для {new_agent.email}")
                return False
        except Exception as owner_error:
            print(f"⚠️ Помилка пошуку HubSpot owner: {owner_error}")
            app.logger.warning(f"⚠️ Помилка пошуку HubSpot owner для {new_agent.email}: {owner_error}")
            return False
        
        # Оновлюємо hubspot_owner_id в угоді
        from hubspot.crm.deals import SimplePublicObjectInput
        deal_properties = {"hubspot_owner_id": hubspot_owner_id}
        deal_input = SimplePublicObjectInput(properties=deal_properties)
        
        hubspot_client.crm.deals.basic_api.update(
            deal_id=lead.hubspot_deal_id,
            simple_public_object_input=deal_input
        )
        
        print(f"✅ Оновлено HubSpot owner для ліда {lead.id}: {hubspot_owner_id}")
        app.logger.info(f"✅ Оновлено HubSpot owner для ліда {lead.id}: {hubspot_owner_id}")
        return True
        
    except Exception as e:
        print(f"❌ Помилка оновлення HubSpot owner: {e}")
        app.logger.error(f"❌ Помилка оновлення HubSpot owner для ліда {lead.id}: {e}")
        return False

def update_hubspot_dealstage(lead, new_status):
    """Оновлює dealstage в HubSpot при зміні локального статусу"""
    if not hubspot_client or not lead.hubspot_deal_id:
        return False
    
    try:
        # Зворотній маппінг: локальний статус → HubSpot dealstage ID
        reverse_stage_mapping = {
            'new': '3204738258',        # Новая заявка (оновлено)
            'contacted': '3204738259',  # Контакт встановлено (оновлено)
            'qualified': '3204738261',  # Кваліфіковано
            'closed': '3204738267'      # Сделка закрыта
        }
        
        if new_status not in reverse_stage_mapping:
            print(f"⚠️ Немає маппінгу для статусу '{new_status}', dealstage не оновлено")
            return False
        
        hubspot_dealstage = reverse_stage_mapping[new_status]
        
        # Оновлюємо dealstage в HubSpot
        hubspot_client.crm.deals.basic_api.update(
            deal_id=lead.hubspot_deal_id,
            simple_public_object_input={
                "properties": {
                    "dealstage": hubspot_dealstage
                }
            }
        )
        
        print(f"✅ Оновлено HubSpot dealstage для ліда {lead.id}: {new_status} → {hubspot_dealstage}")
        app.logger.info(f"✅ Оновлено HubSpot dealstage для ліда {lead.id}: {new_status} → {hubspot_dealstage}")
        return True
        
    except Exception as e:
        print(f"❌ Помилка оновлення HubSpot dealstage для ліда {lead.id}: {e}")
        app.logger.error(f"Помилка оновлення HubSpot dealstage: {e}")
        return False

def sync_lead_from_hubspot(lead):
    """Синхронізує дані ліда з HubSpot"""
    if not hubspot_client or not lead.hubspot_contact_id:
        print(f"Немає HubSpot клієнта або ID контакту для ліда {lead.id}")
        return False
    
    try:
        print(f"Синхронізуємо лід {lead.id} з HubSpot контактом {lead.hubspot_contact_id}")
        # Отримуємо контакт з HubSpot з усіма необхідними властивостями
        contact = hubspot_client.crm.contacts.basic_api.get_by_id(
            contact_id=lead.hubspot_contact_id,
            properties=[
                "email", "phone", "phone_number", "mobilephone", "hs_phone_number", 
                "firstname", "lastname", "notes_last_contacted", "hs_last_activity_date",
                "phone_number_1", "telegram__cloned_", "messenger__cloned_", "birthdate__cloned_", "company",
                "telegram", "messenger", "birthdate"
            ]
        )
        print(f"Отримано контакт з HubSpot: {contact.properties}")
        
        # Оновлюємо дані ліда
        if contact.properties:
            # Оновлюємо основні дані
            if contact.properties.get('firstname') and contact.properties.get('lastname'):
                lead.deal_name = f"{contact.properties['firstname']} {contact.properties['lastname']}"
            
            # Детальне логування телефонних полів
            print(f"📞 Телефонні поля з HubSpot:")
            print(f"   phone: {contact.properties.get('phone')}")
            print(f"   phone_number: {contact.properties.get('phone_number')}")
            print(f"   mobilephone: {contact.properties.get('mobilephone')}")
            print(f"   hs_phone_number: {contact.properties.get('hs_phone_number')}")
            print(f"   phone_number_1: {contact.properties.get('phone_number_1')}")
            
            # Оновлюємо основний телефон (пріоритет: phone_number > mobilephone > hs_phone_number > phone)
            phone_to_use = None
            source = None
            
            if contact.properties.get('phone_number'):
                phone_to_use = contact.properties['phone_number']
                source = "phone_number"
            elif contact.properties.get('mobilephone'):
                phone_to_use = contact.properties['mobilephone']
                source = "mobilephone"
            elif contact.properties.get('hs_phone_number'):
                phone_to_use = contact.properties['hs_phone_number']
                source = "hs_phone_number"
            elif contact.properties.get('phone'):
                phone_to_use = contact.properties['phone']
                source = "phone"
            
            if phone_to_use:
                lead.phone = phone_to_use
                print(f"✅ Використовуємо {source}: {phone_to_use}")
                print(f"📱 Оновлено номер ліда: {lead.phone}")
            else:
                print(f"⚠️ Жодне phone поле не знайдено в HubSpot!")
            
            # Оновлюємо додаткові контактні дані (другий номер телефону)
            print(f"📞 Перевірка другого номеру телефону:")
            print(f"   phone_number_1: {contact.properties.get('phone_number_1')}")
            if contact.properties.get('phone_number_1'):
                lead.second_phone = contact.properties['phone_number_1']
                print(f"✅ Оновлено другий телефон (phone_number_1): {lead.second_phone}")
            else:
                print(f"⚠️ Другий номер телефону (phone_number_1) не знайдено в HubSpot")
            
            # Мапимо telegram (спочатку без __cloned_, потім з)
            if contact.properties.get('telegram'):
                lead.telegram_nickname = contact.properties['telegram']
                print(f"Оновлено telegram з контакту: {contact.properties['telegram']}")
            elif contact.properties.get('telegram__cloned_'):
                lead.telegram_nickname = contact.properties['telegram__cloned_']
                print(f"Оновлено telegram з контакту (__cloned_): {contact.properties['telegram__cloned_']}")
            
            # Мапимо messenger (спочатку без __cloned_, потім з)
            if contact.properties.get('messenger'):
                lead.messenger = contact.properties['messenger']
                print(f"Оновлено messenger з контакту: {contact.properties['messenger']}")
            elif contact.properties.get('messenger__cloned_'):
                lead.messenger = contact.properties['messenger__cloned_']
                print(f"Оновлено messenger з контакту (__cloned_): {contact.properties['messenger__cloned_']}")
            
            # Мапимо birthdate (спочатку без __cloned_, потім з)
            print(f"🎂 Перевірка дати народження:")
            print(f"   birthdate: {contact.properties.get('birthdate')}")
            print(f"   birthdate__cloned_: {contact.properties.get('birthdate__cloned_')}")
            
            birth_date_value = None
            birth_date_source = None
            if contact.properties.get('birthdate'):
                birth_date_value = contact.properties['birthdate']
                birth_date_source = "birthdate"
            elif contact.properties.get('birthdate__cloned_'):
                birth_date_value = contact.properties['birthdate__cloned_']
                birth_date_source = "birthdate__cloned_"
            
            if birth_date_value:
                try:
                    from datetime import datetime
                    birth_date = datetime.strptime(birth_date_value, '%Y-%m-%d').date()
                    lead.birth_date = birth_date
                    print(f"✅ Оновлено дату народження з {birth_date_source}: {birth_date_value} → {birth_date}")
                except (ValueError, TypeError) as e:
                    print(f"❌ Не вдалося перетворити дату народження з контакту: {birth_date_value} (помилка: {e})")
            else:
                print(f"⚠️ Дата народження не знайдена в HubSpot")
            
            if contact.properties.get('company'):
                lead.company = contact.properties['company']
            
            # Оновлюємо нотатки в полі lead.notes (старий спосіб)
            if contact.properties.get('notes_last_contacted'):
                if not lead.notes or contact.properties['notes_last_contacted'] not in lead.notes:
                    lead.notes = (lead.notes or '') + '\n' + contact.properties['notes_last_contacted']
        
        # Отримуємо угоду з HubSpot
        if lead.hubspot_deal_id:
            print(f"Отримуємо угоду з HubSpot: {lead.hubspot_deal_id}")
            deal = hubspot_client.crm.deals.basic_api.get_by_id(
                deal_id=lead.hubspot_deal_id,
                properties=[
                    "dealname", "dealstage", "amount", "closedate", "budget", "language", 
                    "source_channel", "deal_closed", "decline_reason", "purchase_reason__cloned_",
                    "property_type__cloned_", "property_status__cloned_", "purchase_reason",
                    "hubspot_owner_id", "purchase_country", "telegram", "messenger", "birthdate",
                    "responisble_agent", "from_agent_portal__name_"
                ]
            )
            print(f"Отримано угоду з HubSpot: {deal.properties}")
            
            if deal.properties:
                # Оновлюємо статус угоди з HubSpot dealstage
                if deal.properties.get('dealstage'):
                    # Мапимо всі стадії HubSpot (dealstage ID) на наші статуси
                    stage_mapping = {
                        # Нові заявки (валідний ID)
                        '3204738258': 'new',        # Новая заявка
                        
                        # Контакт встановлено (валідний ID)
                        '3204738259': 'contacted',  # Контакт встановлено
                        
                        # Кваліфіковані ліди (валідні ID)
                        '3204738261': 'qualified',  # Кваліфіковано
                        '3204738262': 'qualified',  # Встреча проведена
                        '3204738265': 'qualified',  # Переговоры
                        '3204738266': 'qualified',  # Задаток
                        
                        # Закриті угоди (валідний ID)
                        '3204738267': 'closed'      # Сделка закрыта
                    }
                    
                    # Маппінг ID стадій на їх назви (тільки валідні ID)
                    stage_labels = {
                        '3204738258': 'Новая заявка',
                        '3204738259': 'Контакт встановлено',
                        '3204738261': 'Назначена встреча',
                        '3204738262': 'Встреча проведена',
                        '3204738265': 'Переговоры',
                        '3204738266': 'Задаток',
                        '3204738267': 'Сделка закрыта'
                    }
                    
                    hubspot_stage = deal.properties['dealstage']
                    print(f"🔄 HubSpot dealstage: {hubspot_stage}")
                    
                    # Зберігаємо оригінальну назву стадії з HubSpot
                    if hubspot_stage in stage_labels:
                        lead.hubspot_stage_label = stage_labels[hubspot_stage]
                        print(f"   Стадія HubSpot: {lead.hubspot_stage_label}")
                    
                    if hubspot_stage in stage_mapping:
                        old_status = lead.status
                        lead.status = stage_mapping[hubspot_stage]
                        print(f"   Оновлено статус: {old_status} → {lead.status}")
                    else:
                        print(f"⚠️ Невідомий dealstage ID: {hubspot_stage}, статус не оновлено")
                        # Логуємо невідомий dealstage для подальшого додавання в маппінг
                        app.logger.warning(f"Невідомий HubSpot dealstage: {hubspot_stage} для ліда {lead.id}")
                
                # Оновлюємо суму
                if deal.properties.get('amount'):
                    amount = deal.properties['amount']
                    # Перетворюємо в число, якщо це рядок
                    try:
                        amount = float(amount) if isinstance(amount, str) else amount
                        # Мапимо суму на наші бюджетні категорії
                        if amount <= 200000:
                            lead.budget = 'до 200к'
                        elif amount <= 500000:
                            lead.budget = '200к–500к'
                        elif amount <= 1000000:
                            lead.budget = '500к–1млн'
                        else:
                            lead.budget = '1млн+'
                    except (ValueError, TypeError):
                        print(f"Не вдалося перетворити суму {amount} в число")
                
                # Оновлюємо додаткові властивості угоди
                if deal.properties.get('budget'):
                    lead.budget = deal.properties['budget']
                
                if deal.properties.get('language'):
                    lead.communication_language = deal.properties['language']
                
                if deal.properties.get('source_channel'):
                    lead.source = deal.properties['source_channel']
                
                if deal.properties.get('decline_reason'):
                    lead.refusal_reason = deal.properties['decline_reason']
                
                # Мапимо purchase_reason (спочатку з __cloned_, потім без)
                if deal.properties.get('purchase_reason__cloned_'):
                    lead.purchase_goal = deal.properties['purchase_reason__cloned_']
                elif deal.properties.get('purchase_reason'):
                    lead.purchase_goal = deal.properties['purchase_reason']
                
                if deal.properties.get('property_type__cloned_'):
                    lead.property_type = deal.properties['property_type__cloned_']
                
                if deal.properties.get('property_status__cloned_'):
                    # Це поле може бути пов'язане з object_type або створити нове поле
                    lead.object_type = deal.properties['property_status__cloned_']
                
                # Оновлюємо країну покупки
                if deal.properties.get('purchase_country'):
                    lead.country = deal.properties['purchase_country']
                
                # Оновлюємо telegram з угоди (перезаписуємо, якщо є в угоді)
                if deal.properties.get('telegram'):
                    lead.telegram_nickname = deal.properties['telegram']
                    print(f"Оновлено telegram з угоди: {deal.properties['telegram']}")
                
                # Оновлюємо messenger з угоди (перезаписуємо, якщо є в угоді)
                if deal.properties.get('messenger'):
                    lead.messenger = deal.properties['messenger']
                    print(f"Оновлено messenger з угоди: {deal.properties['messenger']}")
                
                # Оновлюємо birthdate з угоди (перезаписуємо, якщо є в угоді)
                if deal.properties.get('birthdate'):
                    try:
                        from datetime import datetime
                        birth_date = datetime.strptime(deal.properties['birthdate'], '%Y-%m-%d').date()
                        lead.birth_date = birth_date
                        print(f"Оновлено birthdate з угоди: {deal.properties['birthdate']}")
                    except (ValueError, TypeError):
                        print(f"Не вдалося перетворити дату народження з угоди: {deal.properties['birthdate']}")
                
                # Оновлюємо deal name з HubSpot (якщо є)
                if deal.properties.get('dealname'):
                    lead.deal_name = deal.properties['dealname']
                    print(f"Оновлено deal_name з HubSpot: {lead.deal_name}")
                
                # Оновлюємо responisble_agent з HubSpot
                if deal.properties.get('responisble_agent'):
                    # Зберігаємо HubSpot responsible agent в notes
                    if not lead.notes or "HubSpot Responsible Agent:" not in lead.notes:
                        lead.notes = f"HubSpot Responsible Agent: {deal.properties['responisble_agent']}"
                    print(f"HubSpot відповідальний агент: {deal.properties['responisble_agent']}")
                
                # Синхронізуємо агента з поля from_agent_portal__name_ (пріоритет 1)
                if deal.properties.get('from_agent_portal__name_'):
                    agent_name = deal.properties['from_agent_portal__name_'].strip()
                    if agent_name:
                        agent_user = User.query.filter_by(username=agent_name).first()
                        if agent_user and agent_user.id != lead.agent_id:
                            print(f"🔄 Синхронізація агента з from_agent_portal__name_ ({agent_name}) для ліда {lead.id}")
                            old_agent_id = lead.agent_id
                            lead.agent_id = agent_user.id
                            app.logger.info(f"🔄 Синхронізовано agent_id для ліда {lead.id}: {old_agent_id} → {agent_user.id} (з from_agent_portal__name_: {agent_name})")
                        elif agent_user:
                            print(f"✅ Агент з from_agent_portal__name_ ({agent_name}) вже встановлений для ліда {lead.id}")
                        else:
                            print(f"⚠️ Агент з username {agent_name} (from_agent_portal__name_) не знайдено в системі для ліда {lead.id}")
                
                # Оновлюємо deal owner (власника угоди) - завжди синхронізуємо з HubSpot (для notes)
                # Синхронізуємо agent_id на основі hubspot_owner_id тільки якщо from_agent_portal__name_ не встановлено (пріоритет 2)
                if deal.properties.get('hubspot_owner_id'):
                    try:
                        # Отримуємо інформацію про власника
                        owner = hubspot_client.crm.owners.owners_api.get_by_id(
                            owner_id=deal.properties['hubspot_owner_id']
                        )
                        if owner:
                            # Формуємо ім'я власника
                            owner_name = ""
                            if owner.first_name and owner.last_name:
                                owner_name = f"{owner.first_name} {owner.last_name}"
                            elif owner.first_name:
                                owner_name = owner.first_name
                            elif owner.last_name:
                                owner_name = owner.last_name
                            elif owner.email:
                                # Якщо імен немає, використовуємо email
                                owner_name = owner.email
                            
                            if owner_name:
                                # Завжди оновлюємо HubSpot Deal Owner в notes (навіть якщо вже є)
                                import re
                                owner_pattern = r'HubSpot Deal Owner:\s*[^\n]*'
                                new_owner_text = f'HubSpot Deal Owner: {owner_name}'
                                
                                if lead.notes and re.search(owner_pattern, lead.notes):
                                    # Замінюємо старе значення на нове
                                    lead.notes = re.sub(owner_pattern, new_owner_text, lead.notes)
                                else:
                                    # Додаємо нове значення
                                    if lead.notes:
                                        lead.notes = (lead.notes.rstrip() + "\n" + new_owner_text).strip()
                                    else:
                                        lead.notes = new_owner_text
                                
                                print(f"✅ Оновлено HubSpot власника угоди: {owner_name}")
                                app.logger.info(f"✅ Оновлено HubSpot власника угоди для ліда {lead.id}: {owner_name}")
                                
                                # Синхронізуємо agent_id на основі HubSpot owner email (тільки якщо from_agent_portal__name_ не встановлено)
                                if not deal.properties.get('from_agent_portal__name_') and owner.email:
                                    # Шукаємо агента в системі по email
                                    agent_by_email = User.query.filter_by(email=owner.email.lower()).first()
                                    if agent_by_email and agent_by_email.id != lead.agent_id:
                                        print(f"🔄 Зміна агента: {lead.agent_id} → {agent_by_email.id} ({owner.email})")
                                        old_agent_id = lead.agent_id
                                        lead.agent_id = agent_by_email.id
                                        app.logger.info(f"🔄 Синхронізовано agent_id для ліда {lead.id}: {old_agent_id} → {agent_by_email.id} (з HubSpot owner email)")
                                    elif not agent_by_email:
                                        print(f"⚠️ Агент з email {owner.email} не знайдено в системі")
                                        app.logger.warning(f"⚠️ Агент з email {owner.email} (HubSpot owner) не знайдено в системі для ліда {lead.id}")
                    except Exception as e:
                        print(f"❌ Помилка отримання власника угоди: {e}")
                        app.logger.error(f"❌ Помилка отримання HubSpot owner для ліда {lead.id}: {e}")
        
        # Синхронізуємо активності з HubSpot
        sync_activities_from_hubspot(lead)
        
        # Оновлюємо час останньої синхронізації
        lead.last_sync_at = get_ukraine_time()
        
        db.session.commit()
        print(f"Лід {lead.id} синхронізовано з HubSpot")
        return True
        
    except Exception as e:
        print(f"Помилка синхронізації ліда {lead.id}: {e}")
        return False

def sync_all_leads_from_hubspot():
    """Синхронізує всі ліді з HubSpot"""
    if not hubspot_client:
        return False
    
    leads = Lead.query.filter(Lead.hubspot_contact_id.isnot(None)).all()
    synced_count = 0
    
    for lead in leads:
        if sync_lead_from_hubspot(lead):
            synced_count += 1
    
    print(f"Синхронізовано {synced_count} з {len(leads)} лідів")
    return synced_count > 0

def fetch_all_deals_from_hubspot():
    """Завантажує всі deals з HubSpot та створює/оновлює ліди в локальній БД"""
    if not hubspot_client:
        print("⚠️ HubSpot API не налаштований")
        app.logger.warning("HubSpot API не налаштований для завантаження deals")
        return {'created': 0, 'updated': 0, 'errors': 0}
    
    try:
        print("🔄 Початок завантаження всіх deals з HubSpot...")
        app.logger.info("🔄 Початок завантаження всіх deals з HubSpot...")
        
        created_count = 0
        updated_count = 0
        errors_count = 0
        
        # Pipeline IDs та stages для фільтрації
        pipeline_configs = {
            'default': {
                'stages': ['appointmentscheduled', '3204738245', '3204738246', '3523602653', '3523660994']
            },
            '2341107958': {
                'stages': ['3204738258', '3204738259', '3204738261', '3204738262', '3204738265', '3204738266', '3204738267']
            },
            '2346002665': {
                'stages': ['3206386874', '3206386875', '3206386876', '3206386877', '3206386878', '3206386879', '3206344915']
            }
        }
        
        # Отримуємо deals з кожного pipeline та stage окремо
        for pipeline_id, config in pipeline_configs.items():
            stages = config['stages']
            print(f"🔄 Завантаження deals з pipeline {pipeline_id} (stages: {len(stages)})...")
            app.logger.info(f"🔄 Завантаження deals з pipeline {pipeline_id} (stages: {len(stages)})...")
            
            # Обробляємо кожен stage окремо
            for stage_id in stages:
                after = None
                page = 0
                max_pages = 1000  # До 100,000 deals на stage
                
                while page < max_pages:
                    try:
                        # Властивості, які потрібні для deals
                        # phone_number - це поле в deal, а не в контакті!
                        properties = [
                            'dealname', 'dealstage', 'amount', 'closedate', 'createdate',
                            'hubspot_owner_id', 'responisble_agent', 'from_agent_portal__name_',
                            'birthdate', 'pipeline', 'phone_number', 'hs_object_id'
                        ]
                        
                        # Використовуємо search API для фільтрації по pipeline та stage
                        from hubspot.crm.deals import PublicObjectSearchRequest
                        from hubspot.crm.deals import Filter, FilterGroup
                        
                        # Створюємо фільтр по pipeline та dealstage
                        filters = []
                        
                        # Фільтр по pipeline
                        if pipeline_id == 'default':
                            # Для default pipeline використовуємо фільтр, що pipeline порожній або default
                            filters.append(
                                Filter(
                                    property_name='pipeline',
                                    operator='EQ',
                                    value='default'
                                )
                            )
                        else:
                            filters.append(
                                Filter(
                                    property_name='pipeline',
                                    operator='EQ',
                                    value=pipeline_id
                                )
                            )
                        
                        # Фільтр по dealstage
                        filters.append(
                            Filter(
                                property_name='dealstage',
                                operator='EQ',
                                value=stage_id
                            )
                        )
                        
                        search_request = PublicObjectSearchRequest(
                            filter_groups=[FilterGroup(filters=filters)],
                            properties=properties,
                            limit=100,
                            after=after
                        )
                        
                        # Виконуємо пошук
                        deals_response = hubspot_client.crm.deals.search_api.do_search(
                            public_object_search_request=search_request
                        )
                        
                        if not deals_response.results:
                            break
                        
                        print(f"📄 Pipeline {pipeline_id}, stage {stage_id}, сторінка {page + 1}: отримано {len(deals_response.results)} deals")
                        app.logger.info(f"📄 Pipeline {pipeline_id}, stage {stage_id}, сторінка {page + 1}: отримано {len(deals_response.results)} deals")
                        
                        # Обробляємо кожен deal
                        for deal in deals_response.results:
                            try:
                                # Використовуємо hs_object_id як deal_id
                                deal_id = str(deal.properties.get('hs_object_id') or deal.id)
                                deal_properties = deal.properties
                                
                                # Отримуємо phone_number прямо з deal properties
                                phone = deal_properties.get('phone_number')
                                
                                if not phone:
                                    print(f"⚠️ Deal {deal_id} не має phone_number, пропускаємо")
                                    continue
                                
                                # Форматуємо телефон
                                try:
                                    parsed_phone = phonenumbers.parse(phone, None)
                                    formatted_phone = phonenumbers.format_number(
                                        parsed_phone, 
                                        phonenumbers.PhoneNumberFormat.INTERNATIONAL
                                    )
                                except:
                                    formatted_phone = phone
                                
                                # Отримуємо контакт, пов'язаний з deal (для email та імені)
                                contact_id = None
                                email = ''
                                deal_name = deal_properties.get('dealname', '')
                                
                                try:
                                    # Отримуємо асоціації контакту з deal
                                    # Використовуємо правильний API шлях (без v4)
                                    associations = hubspot_client.crm.associations.basic_api.get_page(
                                        from_object_type='deals',
                                        from_object_id=deal_id,
                                        to_object_type='contacts'
                                    )
                                    if associations.results:
                                        # Отримуємо перший контакт з асоціацій
                                        contact_id = str(associations.results[0].to_object_id)
                                        
                                        # Отримуємо дані контакту для email та імені
                                        try:
                                            contact = hubspot_client.crm.contacts.basic_api.get_by_id(
                                                contact_id=contact_id,
                                                properties=['email', 'firstname', 'lastname']
                                            )
                                            if contact.properties:
                                                email = contact.properties.get('email', '')
                                                firstname = contact.properties.get('firstname', '')
                                                lastname = contact.properties.get('lastname', '')
                                                
                                                # Якщо немає dealname, використовуємо ім'я з контакту
                                                if not deal_name:
                                                    if firstname and lastname:
                                                        deal_name = f"{firstname} {lastname}"
                                                    elif firstname:
                                                        deal_name = firstname
                                                    elif lastname:
                                                        deal_name = lastname
                                        except Exception as contact_error:
                                            print(f"⚠️ Помилка отримання контакту {contact_id}: {contact_error}")
                                except Exception as assoc_error:
                                    # Помилка з асоціаціями не критична - продовжуємо без контакту
                                    app.logger.debug(f"⚠️ Помилка отримання асоціацій для deal {deal_id}: {assoc_error}")
                                    # Не виводимо в консоль, щоб не засмічувати логи
                                
                                # Якщо немає email, використовуємо phone як унікальний ідентифікатор
                                if not email:
                                    email = f"no-email-{deal_id}@hubspot.local"
                                
                                # Якщо немає deal_name, використовуємо phone
                                if not deal_name:
                                    deal_name = f"Deal {deal_id}"
                                
                                # Визначаємо агента (за замовчуванням перший адмін або перший агент)
                                default_agent = User.query.filter(
                                    (User.role == 'admin') | (User.role == 'agent')
                                ).first()
                                
                                # Спробуємо знайти агента за полем from_agent_portal__name_ (пріоритет 1)
                                agent_id = None
                                if deal_properties.get('from_agent_portal__name_'):
                                    agent_name = deal_properties['from_agent_portal__name_'].strip()
                                    if agent_name:
                                        agent_user = User.query.filter_by(username=agent_name).first()
                                        if agent_user:
                                            agent_id = agent_user.id
                                            print(f"✅ Знайдено агента за from_agent_portal__name_ ({agent_name}) для deal {deal_id}")
                                
                                # Якщо агент не знайдено за from_agent_portal__name_, спробуємо за email з HubSpot owner (пріоритет 2)
                                if not agent_id and deal_properties.get('hubspot_owner_id'):
                                    try:
                                        owner = hubspot_client.crm.owners.owners_api.get_by_id(
                                            owner_id=deal_properties['hubspot_owner_id']
                                        )
                                        if owner and owner.email:
                                            owner_user = User.query.filter_by(email=owner.email).first()
                                            if owner_user:
                                                agent_id = owner_user.id
                                                print(f"✅ Знайдено агента за hubspot_owner_id email ({owner.email}) для deal {deal_id}")
                                    except Exception as owner_error:
                                        app.logger.debug(f"⚠️ Помилка отримання owner: {owner_error}")
                                
                                # Якщо агент не знайдено, використовуємо default_agent
                                if not agent_id:
                                    if default_agent:
                                        agent_id = default_agent.id
                                        print(f"ℹ️ Використано агента за замовчуванням ({default_agent.username}) для deal {deal_id}")
                                    else:
                                        # Якщо взагалі немає агентів в системі - пропускаємо
                                        print(f"⚠️ Немає агентів в системі для deal {deal_id}, пропускаємо")
                                        continue
                                
                                # Визначаємо статус з deal stage
                                status = 'new'
                                deal_stage = deal_properties.get('dealstage', '')
                                if deal_stage:
                                    # Мапінг стадій HubSpot на статуси системи
                                    if 'closedwon' in deal_stage.lower() or 'closed won' in deal_stage.lower():
                                        status = 'closed'
                                    elif 'qualified' in deal_stage.lower():
                                        status = 'qualified'
                                    elif 'contacted' in deal_stage.lower():
                                        status = 'contacted'
                                
                                # Визначаємо budget (з amount)
                                budget = None
                                if deal_properties.get('amount'):
                                    try:
                                        amount = float(deal_properties['amount'])
                                        if amount < 200000:
                                            budget = 'до 200к'
                                        elif amount < 500000:
                                            budget = '200к–500к'
                                        elif amount < 1000000:
                                            budget = '500к–1млн'
                                        else:
                                            budget = '1млн+'
                                    except:
                                        pass
                                
                                # Перевіряємо, чи існує лід з цим deal_id
                                existing_lead = Lead.query.filter_by(hubspot_deal_id=deal_id).first()
                                
                                if existing_lead:
                                    # Оновлюємо існуючий лід
                                    existing_lead.deal_name = deal_name
                                    existing_lead.email = email
                                    existing_lead.phone = formatted_phone
                                    if budget:
                                        existing_lead.budget = budget
                                    existing_lead.status = status
                                    if contact_id:
                                        existing_lead.hubspot_contact_id = contact_id
                                    existing_lead.hubspot_deal_id = deal_id
                                    existing_lead.agent_id = agent_id
                                    
                                    updated_count += 1
                                    print(f"✅ Оновлено лід {existing_lead.id} з HubSpot deal {deal_id}")
                                else:
                                    # Перевіряємо, чи не існує лід з таким телефоном
                                    duplicate_lead = Lead.query.filter(
                                        Lead.phone == formatted_phone
                                    ).first()
                                    
                                    if duplicate_lead:
                                        # Якщо знайдено дублікат, оновлюємо його
                                        duplicate_lead.hubspot_deal_id = deal_id
                                        if contact_id:
                                            duplicate_lead.hubspot_contact_id = contact_id
                                        duplicate_lead.agent_id = agent_id
                                        if budget:
                                            duplicate_lead.budget = budget
                                        duplicate_lead.status = status
                                        updated_count += 1
                                        print(f"✅ Оновлено дублікат ліда {duplicate_lead.id} з HubSpot deal {deal_id}")
                                    else:
                                        # Створюємо новий лід
                                        new_lead = Lead(
                                            agent_id=agent_id,
                                            deal_name=deal_name,
                                            email=email,
                                            phone=formatted_phone,
                                            budget=budget or 'до 200к',
                                            status=status,
                                            hubspot_contact_id=contact_id,
                                            hubspot_deal_id=deal_id
                                        )
                                        
                                        db.session.add(new_lead)
                                        created_count += 1
                                        print(f"✅ Створено новий лід з HubSpot deal {deal_id} (phone: {formatted_phone})")
                            
                            except Exception as deal_error:
                                print(f"❌ Помилка обробки deal {deal.id}: {deal_error}")
                                app.logger.error(f"❌ Помилка обробки deal {deal.id}: {deal_error}")
                                errors_count += 1
                                traceback.print_exc()
                    
                        # Перевіряємо, чи є ще сторінки
                        if not deals_response.paging or not deals_response.paging.next:
                            break
                        
                        after = deals_response.paging.next.after
                        page += 1
                        
                        # Додаємо затримку між сторінками для rate limiting
                        time.sleep(0.5)
                        
                        # Комітимо кожні 10 сторінок для зменшення навантаження на БД
                        if page % 10 == 0:
                            db.session.commit()
                            print(f"💾 Збережено прогрес pipeline {pipeline_id}, stage {stage_id}: сторінка {page}")
                    
                    except Exception as page_error:
                        print(f"❌ Помилка отримання сторінки {page + 1} pipeline {pipeline_id}, stage {stage_id}: {page_error}")
                        app.logger.error(f"❌ Помилка отримання сторінки {page + 1} pipeline {pipeline_id}, stage {stage_id}: {page_error}")
                        errors_count += 1
                        break
        
        db.session.commit()
        
        result = {
            'created': created_count,
            'updated': updated_count,
            'errors': errors_count,
            'total_processed': created_count + updated_count
        }
        
        print(f"✅ Завантаження завершено: створено {created_count}, оновлено {updated_count}, помилок {errors_count}")
        app.logger.info(f"✅ Завантаження HubSpot завершено: створено {created_count}, оновлено {updated_count}, помилок {errors_count}")
        
        return result
        
    except Exception as e:
        print(f"❌ Критична помилка при завантаженні deals з HubSpot: {e}")
        app.logger.error(f"❌ Критична помилка при завантаженні deals з HubSpot: {e}")
        traceback.print_exc()
        db.session.rollback()
        return {'created': 0, 'updated': 0, 'errors': 1, 'total_processed': 0}

def fetch_all_contacts_from_hubspot():
    """Завантажує всі контакти з HubSpot CRM та створює/оновлює ліди в локальній БД"""
    if not hubspot_client:
        print("⚠️ HubSpot API не налаштований")
        app.logger.warning("HubSpot API не налаштований для завантаження контактів")
        return {'created': 0, 'updated': 0, 'errors': 0}
    
    try:
        print("🔄 Початок завантаження всіх контактів з HubSpot CRM...")
        app.logger.info("🔄 Початок завантаження всіх контактів з HubSpot CRM...")
        
        created_count = 0
        updated_count = 0
        errors_count = 0
        
        # Отримуємо всі контакти з HubSpot (посторінково)
        after = None
        page = 0
        max_pages = 1000  # До 100,000 контактів
        
        while page < max_pages:
            try:
                # Властивості, які потрібні для контактів
                properties = [
                    'phone', 'phone_number', 'mobilephone', 'hs_phone_number',
                    'phone_number_1', 'email', 'firstname', 'lastname',
                    'company', 'telegram', 'telegram__cloned_', 'messenger',
                    'messenger__cloned_', 'birthdate', 'birthdate__cloned_'
                ]
                
                # Отримуємо сторінку контактів
                if after:
                    contacts_response = hubspot_client.crm.contacts.basic_api.get_page(
                        limit=100,
                        after=after,
                        properties=properties
                    )
                else:
                    contacts_response = hubspot_client.crm.contacts.basic_api.get_page(
                        limit=100,
                        properties=properties
                    )
                
                if not contacts_response.results:
                    break
                
                print(f"📄 Сторінка {page + 1}: отримано {len(contacts_response.results)} контактів")
                app.logger.info(f"📄 Сторінка {page + 1}: отримано {len(contacts_response.results)} контактів")
                
                # Обробляємо кожен контакт
                for contact in contacts_response.results:
                    try:
                        contact_id = str(contact.id)
                        contact_properties = contact.properties
                        
                        # Визначаємо основний телефон
                        phone = None
                        if contact_properties.get('phone_number'):
                            phone = contact_properties['phone_number']
                        elif contact_properties.get('mobilephone'):
                            phone = contact_properties['mobilephone']
                        elif contact_properties.get('hs_phone_number'):
                            phone = contact_properties['hs_phone_number']
                        elif contact_properties.get('phone'):
                            phone = contact_properties['phone']
                        
                        # Пропускаємо контакти без телефону
                        if not phone:
                            continue
                        
                        # Форматуємо телефон
                        try:
                            parsed_phone = phonenumbers.parse(phone, None)
                            formatted_phone = phonenumbers.format_number(
                                parsed_phone, 
                                phonenumbers.PhoneNumberFormat.INTERNATIONAL
                            )
                        except:
                            formatted_phone = phone
                        
                        # Визначаємо email
                        email = contact_properties.get('email', '')
                        if not email:
                            # Якщо немає email, використовуємо phone як унікальний ідентифікатор
                            email = f"no-email-{contact_id}@hubspot.local"
                        
                        # Визначаємо ім'я
                        firstname = contact_properties.get('firstname', '')
                        lastname = contact_properties.get('lastname', '')
                        if firstname and lastname:
                            deal_name = f"{firstname} {lastname}"
                        elif firstname:
                            deal_name = firstname
                        elif lastname:
                            deal_name = lastname
                        else:
                            deal_name = email.split('@')[0] if email else f"Contact {contact_id}"
                        
                        # Визначаємо агента (за замовчуванням перший адмін або перший агент)
                        default_agent = User.query.filter(
                            (User.role == 'admin') | (User.role == 'agent')
                        ).first()
                        agent_id = default_agent.id if default_agent else None
                        
                        # Перевіряємо, чи існує лід з цим contact_id
                        existing_lead = Lead.query.filter_by(hubspot_contact_id=contact_id).first()
                        
                        if existing_lead:
                            # Оновлюємо існуючий лід
                            existing_lead.deal_name = deal_name
                            existing_lead.email = email
                            existing_lead.phone = formatted_phone
                            existing_lead.hubspot_contact_id = contact_id
                            if agent_id:
                                existing_lead.agent_id = agent_id
                            
                            # Оновлюємо додаткові поля
                            if contact_properties.get('phone_number_1'):
                                existing_lead.second_phone = contact_properties['phone_number_1']
                            if contact_properties.get('telegram') or contact_properties.get('telegram__cloned_'):
                                existing_lead.telegram_nickname = contact_properties.get('telegram') or contact_properties.get('telegram__cloned_')
                            if contact_properties.get('messenger') or contact_properties.get('messenger__cloned_'):
                                existing_lead.messenger = contact_properties.get('messenger') or contact_properties.get('messenger__cloned_')
                            if contact_properties.get('company'):
                                existing_lead.company = contact_properties['company']
                            
                            updated_count += 1
                            print(f"✅ Оновлено лід {existing_lead.id} з HubSpot контакту {contact_id}")
                        else:
                            # Перевіряємо, чи не існує лід з таким телефоном або email
                            duplicate_lead = Lead.query.filter(
                                (Lead.phone == formatted_phone) | (Lead.email == email)
                            ).first()
                            
                            if duplicate_lead:
                                # Якщо знайдено дублікат, оновлюємо його
                                duplicate_lead.hubspot_contact_id = contact_id
                                if agent_id:
                                    duplicate_lead.agent_id = agent_id
                                updated_count += 1
                                print(f"✅ Оновлено дублікат ліда {duplicate_lead.id} з HubSpot контакту {contact_id}")
                            else:
                                # Створюємо новий лід
                                new_lead = Lead(
                                    agent_id=agent_id,
                                    deal_name=deal_name,
                                    email=email,
                                    phone=formatted_phone,
                                    budget='до 200к',
                                    status='new',
                                    hubspot_contact_id=contact_id,
                                    second_phone=contact_properties.get('phone_number_1'),
                                    telegram_nickname=contact_properties.get('telegram') or contact_properties.get('telegram__cloned_'),
                                    messenger=contact_properties.get('messenger') or contact_properties.get('messenger__cloned_'),
                                    company=contact_properties.get('company')
                                )
                                
                                db.session.add(new_lead)
                                created_count += 1
                                print(f"✅ Створено новий лід з HubSpot контакту {contact_id}")
                        
                    except Exception as contact_error:
                        print(f"❌ Помилка обробки контакту {contact.id}: {contact_error}")
                        app.logger.error(f"❌ Помилка обробки контакту {contact.id}: {contact_error}")
                        errors_count += 1
                        traceback.print_exc()
                
                # Перевіряємо, чи є ще сторінки
                if not contacts_response.paging or not contacts_response.paging.next:
                    break
                
                after = contacts_response.paging.next.after
                page += 1
                
                # Додаємо затримку між сторінками для rate limiting
                time.sleep(0.5)
                
                # Комітимо кожні 100 контактів для зменшення навантаження на БД
                if page % 10 == 0:
                    db.session.commit()
                    print(f"💾 Збережено прогрес: сторінка {page}")
                
            except Exception as page_error:
                print(f"❌ Помилка отримання сторінки {page + 1}: {page_error}")
                app.logger.error(f"❌ Помилка отримання сторінки {page + 1}: {page_error}")
                errors_count += 1
                break
        
        db.session.commit()
        
        result = {
            'created': created_count,
            'updated': updated_count,
            'errors': errors_count,
            'total_processed': created_count + updated_count
        }
        
        print(f"✅ Завантаження контактів завершено: створено {created_count}, оновлено {updated_count}, помилок {errors_count}")
        app.logger.info(f"✅ Завантаження HubSpot контактів завершено: створено {created_count}, оновлено {updated_count}, помилок {errors_count}")
        
        return result
        
    except Exception as e:
        print(f"❌ Критична помилка при завантаженні контактів з HubSpot: {e}")
        app.logger.error(f"❌ Критична помилка при завантаженні контактів з HubSpot: {e}")
        traceback.print_exc()
        db.session.rollback()
        return {'created': 0, 'updated': 0, 'errors': 1, 'total_processed': 0}

def background_sync_task():
    """Фонова задача для автоматичної синхронізації лідів"""
    print("🔄 Запущено фонову синхронізацію")
    app.logger.info("🔄 Фонова синхронізація HubSpot запущена")
    
    last_full_sync = 0  # Час останньої повної синхронізації (в секундах)
    full_sync_interval = 3600  # 1 година для повної синхронізації
    
    while True:
        try:
            current_time = time.time()
            
            # Повна синхронізація (завантаження всіх deals з HubSpot) раз на годину
            # Звірка йде по deals, тому завантажуємо deals, а не контакти
            if current_time - last_full_sync >= full_sync_interval:
                with app.app_context():
                    if hubspot_client:
                        print("⏰ Початок повної синхронізації з HubSpot (завантаження всіх deals)...")
                        app.logger.info("⏰ Початок повної синхронізації з HubSpot (завантаження всіх deals)...")
                        
                        # Завантажуємо всі deals з HubSpot (з deals береться інформація про номери для звірки)
                        deals_result = fetch_all_deals_from_hubspot()
                        print(f"✅ Deals завантажено: створено {deals_result.get('created', 0)}, оновлено {deals_result.get('updated', 0)}, помилок {deals_result.get('errors', 0)}")
                        app.logger.info(f"✅ Повна синхронізація завершена: створено {deals_result.get('created', 0)}, оновлено {deals_result.get('updated', 0)}")
                        last_full_sync = current_time
                    else:
                        print("⚠️ HubSpot API не налаштований, повна синхронізація пропущена")
            
            # Часткова синхронізація (оновлення існуючих лідів) кожні 5 хвилин
            time.sleep(300)  # Чекаємо 5 хвилин (300 секунд)
            
            with app.app_context():
                if hubspot_client:
                    print("⏰ Початок автоматичної синхронізації існуючих лідів...")
                    sync_all_leads_from_hubspot()
                    print("✅ Автоматична синхронізація завершена")
                else:
                    print("⚠️ HubSpot API не налаштований, синхронізація пропущена")
        except Exception as e:
            print(f"❌ Помилка в фоновій синхронізації: {e}")
            app.logger.error(f"❌ Помилка в фоновій синхронізації: {e}")
            traceback.print_exc()

def start_background_sync():
    """Запускає фонову синхронізацію в окремому потоці"""
    sync_thread = threading.Thread(target=background_sync_task, daemon=True)
    sync_thread.start()
    print("✅ Фонова синхронізація запущена")

# Маршрути
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Логін з rate limiting (максимум 10 спроб на хвилину)"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            user = User.query.filter_by(username=username).first()
            
            if user:
                # Перевіряємо, чи активний акаунт
                if not user.is_active:
                    flash('Ваш акаунт деактивований. Зверніться до адміністратора.')
                    return render_template('login.html')
                
                # Перевіряємо, чи не заблокований акаунт
                if user.is_account_locked():
                    flash('Ваш акаунт тимчасово заблокований через невдалі спроби входу.')
                    return render_template('login.html')
                
                # Перевіряємо пароль
                if user.check_password(password):
                    # Успішний вхід
                    user.last_login = get_ukraine_time()
                    user.reset_login_attempts()
                    db.session.commit()
                    login_user(user)
                    return redirect(url_for('dashboard'), code=302)
                else:
                    # Невдалий вхід
                    user.increment_login_attempts()
                    db.session.commit()
                    flash('Невірне ім\'я користувача або пароль')
            else:
                flash('Невірне ім\'я користувача або пароль')
        else:
            flash('Будь ласка, заповніть всі поля')
    
    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """Сторінка особистого кабінету"""
    # Отримуємо документи користувача
    documents = UserDocument.query.filter_by(user_id=current_user.id).order_by(UserDocument.uploaded_at.desc()).all()
    
    # Для адміна отримуємо список його брокерів
    brokers = []
    if current_user.role == 'admin':
        brokers = User.query.filter_by(admin_id=current_user.id, role='agent').order_by(User.created_at.desc()).all()
    
    return render_template('profile.html', documents=documents, brokers=brokers)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Оновлення профілю користувача"""
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        
        # Перевірка на порожні поля
        if not username or not email:
            return jsonify({'success': False, 'message': 'Всі поля обов\'язкові'})
        
        # Перевірка, чи не зайнято ім'я користувача
        existing_user = User.query.filter(User.username == username, User.id != current_user.id).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Це ім\'я користувача вже зайнято'})
        
        # Перевірка, чи не зайнято email
        existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_email:
            return jsonify({'success': False, 'message': 'Цей email вже використовується'})
        
        # Оновлюємо дані
        current_user.username = username
        current_user.email = email
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Профіль успішно оновлено'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/api/profile/stats')
@login_required
def profile_stats():
    """API для отримання статистики профілю"""
    try:
        # Отримуємо статистику лідів для поточного користувача
        user_id = current_user.id
        
        # Для адміністратора показуємо загальну статистику
        if current_user.role == 'admin':
            leads_stats = {
                'new': Lead.query.filter_by(status='Нова заявка').count(),
                'in_progress': Lead.query.filter(
                    Lead.status.in_(['Обробка', 'Підтвердив інтерес', 'Зателефонував', 'Уточнили потреби'])
                ).count(),
                'converted': Lead.query.filter_by(status='Угода').count(),
                'rejected': Lead.query.filter_by(status='Відмова').count()
            }
        else:
            # Підрахунок лідів по статусам для агента
            leads_stats = {
                'new': Lead.query.filter_by(agent_id=user_id, status='Нова заявка').count(),
                'in_progress': Lead.query.filter(
                    Lead.agent_id == user_id,
                    Lead.status.in_(['Обробка', 'Підтвердив інтерес', 'Зателефонував', 'Уточнили потреби'])
                ).count(),
                'converted': Lead.query.filter_by(agent_id=user_id, status='Угода').count(),
                'rejected': Lead.query.filter_by(agent_id=user_id, status='Відмова').count()
            }
        
        # Статистика конверсії по тижнях (останні 4 тижні)
        from datetime import datetime, timedelta
        
        conversion_labels = []
        conversion_values = []
        
        for i in range(3, -1, -1):
            week_start = datetime.now() - timedelta(weeks=i+1)
            week_end = datetime.now() - timedelta(weeks=i)
            
            if current_user.role == 'admin':
                total_leads = Lead.query.filter(
                    Lead.created_at >= week_start,
                    Lead.created_at < week_end
                ).count()
                
                converted_leads = Lead.query.filter(
                    Lead.status == 'Угода',
                    Lead.created_at >= week_start,
                    Lead.created_at < week_end
                ).count()
            else:
                total_leads = Lead.query.filter(
                    Lead.agent_id == user_id,
                    Lead.created_at >= week_start,
                    Lead.created_at < week_end
                ).count()
                
                converted_leads = Lead.query.filter(
                    Lead.agent_id == user_id,
                    Lead.status == 'Угода',
                    Lead.created_at >= week_start,
                    Lead.created_at < week_end
                ).count()
            
            conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
            
            conversion_labels.append(f'Тиж {4-i}')
            conversion_values.append(round(conversion_rate, 1))
        
        conversion_stats = {
            'labels': conversion_labels,
            'values': conversion_values
        }
        
        # Статистика поінтів
        next_level_points = 2000 if current_user.level == 'bronze' else (
            5000 if current_user.level == 'silver' else (
                10000 if current_user.level == 'gold' else 10000
            )
        )
        
        next_level_name = 'Срібний' if current_user.level == 'bronze' else (
            'Золотий' if current_user.level == 'silver' else (
                'Платиновий' if current_user.level == 'gold' else 'Максимум'
            )
        )
        
        points_stats = {
            'current_points': current_user.points,
            'next_level_points': next_level_points,
            'next_level': next_level_name
        }
        
        return jsonify({
            'success': True,
            'leads_stats': leads_stats,
            'conversion_stats': conversion_stats,
            'points_stats': points_stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Реєстрація нового користувача"""
    app.logger.info("=" * 80)
    app.logger.info(f"🔍 REGISTER: Запит методом {request.method}")
    
    if current_user.is_authenticated:
        app.logger.info(f"👤 Користувач вже авторизований: {current_user.username}, перенаправлення на dashboard")
        return redirect(url_for('dashboard'))
    
    # Отримуємо список адмінів для вибору
    app.logger.info("📋 Отримуємо список адмінів...")
    admins = User.query.filter_by(role='admin').all()
    app.logger.info(f"✅ Знайдено адмінів: {len(admins)}")
    for admin in admins:
        app.logger.info(f"   - {admin.username} (ID: {admin.id}, email: {admin.email})")
    
    # Створюємо форму і заповнюємо choices для admin_id
    app.logger.info("📝 Створюємо форму реєстрації...")
    form = RegistrationForm(request.form)
    app.logger.info(f"   Form data: {request.form.to_dict()}")
    
    # Заповнюємо choices для admin_id (0 замість '' для coerce=int)
    form.admin_id.choices = [(0, '-- Виберіть адміна --')] + [(admin.id, f"{admin.username} ({admin.email})") for admin in admins]
    app.logger.info(f"   Admin choices: {form.admin_id.choices}")
    
    if request.method == 'POST':
        app.logger.info("📥 POST запит - перевірка валідації форми...")
        app.logger.info(f"   username: {form.username.data}")
        app.logger.info(f"   email: {form.email.data}")
        app.logger.info(f"   admin_id: {form.admin_id.data}")
        app.logger.info(f"   password: {'*' * len(form.password.data) if form.password.data else 'None'}")
        app.logger.info(f"   confirm_password: {'*' * len(form.confirm_password.data) if form.confirm_password.data else 'None'}")
        
        # Перевіряємо валідацію
        is_valid = form.validate()
        app.logger.info(f"✅ Валідація форми: {'ПРОЙДЕНО' if is_valid else 'ПРОВАЛЕНО'}")
        
        if not is_valid:
            app.logger.error(f"❌ Помилки валідації форми:")
            for field, errors in form.errors.items():
                for error in errors:
                    app.logger.error(f"   {field}: {error}")
                    flash(f'Помилка поля {field}: {error}', 'error')
            return render_template('register.html', form=form, admins=admins)
        
        app.logger.info("✅ Форма валідна, починаємо обробку...")
        
        # Перевіряємо, чи існує користувач з таким ім'ям або email
        app.logger.info("🔍 Перевіряємо існування користувача...")
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            app.logger.warning(f"⚠️ Користувач з таким ім'ям або email вже існує: {existing_user.username}")
            flash('Користувач з таким ім\'ям або email вже існує')
            return render_template('register.html', form=form, admins=admins)
        
        app.logger.info("✅ Користувач не існує, продовжуємо...")
        
        # Перевіряємо, чи співпадають паролі
        if form.password.data != form.confirm_password.data:
            app.logger.error("❌ Паролі не співпадають")
            flash('Паролі не співпадають')
            return render_template('register.html', form=form, admins=admins)
        
        app.logger.info("✅ Паролі співпадають")
        
        # Перевіряємо, що вибрано адміна
        if not form.admin_id.data or form.admin_id.data == 0:
            app.logger.error("❌ Адміна не вибрано")
            flash('Будь ласка, виберіть адміна')
            return render_template('register.html', form=form, admins=admins)
        
        try:
            # Перевіряємо, що вибраний адмін існує
            app.logger.info(f"🔍 Перевіряємо адміна з ID: {form.admin_id.data}")
            admin = User.query.filter_by(id=form.admin_id.data, role='admin').first()
            if not admin:
                app.logger.error(f"❌ Адмін з ID {form.admin_id.data} не знайдений")
                flash('Вибраний адмін не знайдений')
                return render_template('register.html', form=form, admins=admins)
            
            app.logger.info(f"✅ Адмін знайдено: {admin.username}")
            
            # Створюємо нового користувача (за замовчуванням - агент)
            app.logger.info("💾 Створюємо нового користувача...")
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                role='agent',  # За замовчуванням всі нові користувачі - агенти
                admin_id=form.admin_id.data  # Прив'язуємо до адміна (ОБОВ'ЯЗКОВО)
            )
            new_user.set_password(form.password.data)
            app.logger.info(f"   Користувач створено: {new_user.username} (email: {new_user.email}, role: {new_user.role}, admin_id: {new_user.admin_id})")
            
            app.logger.info("💾 Додаємо користувача до БД...")
            db.session.add(new_user)
            db.session.commit()
            app.logger.info(f"✅ Користувач успішно збережено в БД! User ID: {new_user.id}")
            
            flash(f'Реєстрація успішна! Ви прив\'язані до адміна: {admin.username}. Тепер ви можете увійти в систему.')
            app.logger.info(f"🎉 Реєстрація успішна! Користувач: {new_user.username}, Адмін: {admin.username}")
            app.logger.info("🔄 Перенаправлення на login...")
            app.logger.info("=" * 80)
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"❌ Помилка при реєстрації: {type(e).__name__}: {str(e)}")
            app.logger.error(f"   Traceback: {traceback.format_exc()}")
            flash(f'Помилка при реєстрації: {str(e)}')
            app.logger.info("=" * 80)
            return render_template('register.html', form=form, admins=admins)
    
    app.logger.info("📄 Повертаємо форму реєстрації (GET запит)")
    app.logger.info("=" * 80)
    return render_template('register.html', form=form, admins=admins)

@app.route('/request_verification', methods=['POST'])
@login_required
def request_verification():
    """Запит на верифікацію від агента"""
    if current_user.role == 'admin':
        return jsonify({'success': False, 'message': 'Адміністратори не потребують верифікації'})
    
    if current_user.verification_requested:
        return jsonify({'success': False, 'message': 'Ви вже подавали запит на верифікацію'})
    
    try:
        current_user.verification_requested = True
        current_user.verification_request_date = get_ukraine_time()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Запит на верифікацію подано успішно'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/close_deal/<int:lead_id>', methods=['POST'])
@login_required
def close_deal(lead_id):
    """Закриття угоди та нарахування поінтів"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Перевіряємо доступ до ліда
    if current_user.role == 'agent' and lead.agent_id != current_user.id:
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        # Оновлюємо статус ліда
        lead.status = 'closed'
        lead.notes = (lead.notes or '') + f'\n[Угода закрита {get_ukraine_time().strftime("%d.%m.%Y %H:%M")}]'
        
        # Нараховуємо поінти за закриття угоди
        agent = User.query.get(lead.agent_id)
        if agent:
            agent.add_points(1000)  # 1000 поінтів за закриту угоду
            agent.closed_deals += 1
            print(f"Нараховано 1000 поінтів агенту {agent.username} за закриття угоди")
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Угода успішно закрита! Нараховано 1000 поінтів.',
            'new_points': agent.points if agent else 0
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/delete_lead/<int:lead_id>', methods=['DELETE'])
@login_required
def delete_lead(lead_id):
    """Видалення ліда"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Перевіряємо доступ до ліда
    if current_user.role == 'agent' and lead.agent_id != current_user.id:
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        # Видаляємо пов'язані записи
        Activity.query.filter_by(lead_id=lead_id).delete()
        
        # Видаляємо лід
        lead_name = lead.deal_name
        db.session.delete(lead)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Лід "{lead_name}" успішно видалено.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/verification')
@login_required
def admin_verification():
    """Адмін-панель для верифікації агентів"""
    if current_user.role != 'admin':
        flash('Доступ заборонено')
        return redirect(url_for('dashboard'))
    
    # Отримуємо всіх агентів (сортуємо за датою створення, найновіші зверху)
    all_agents = User.query.filter_by(role='agent').order_by(User.created_at.desc()).all()
    pending_requests = [agent for agent in all_agents if agent.verification_requested and not agent.is_verified]
    verified_agents = [agent for agent in all_agents if agent.is_verified]
    unverified_agents = [agent for agent in all_agents if not agent.verification_requested and not agent.is_verified]
    total_agents = len(all_agents)
    
    return render_template('admin_verification.html', 
                         all_agents=all_agents,
                         pending_requests=pending_requests,
                         verified_agents=verified_agents,
                         unverified_agents=unverified_agents,
                         total_agents=total_agents)

@app.route('/admin/verify_agent', methods=['POST'])
@login_required
def admin_verify_agent():
    """Верифікація або відхилення агента"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    data = request.get_json()
    agent_id = data.get('agent_id')
    approve = data.get('approve', True)
    commission = data.get('commission')
    
    try:
        agent = User.query.get(agent_id)
        if not agent or agent.role != 'agent':
            return jsonify({'success': False, 'message': 'Агент не знайдено'})
        
        if approve:
            # Перевірка наявності комісії при верифікації
            if commission is None:
                return jsonify({'success': False, 'message': 'Необхідно встановити комісію перед верифікацією'})
            
            try:
                commission = float(commission)
                if commission < 0 or commission > 100:
                    return jsonify({'success': False, 'message': 'Комісія має бути від 0% до 100%'})
            except ValueError:
                return jsonify({'success': False, 'message': 'Невірний формат комісії'})
            
            agent.commission = commission
            agent.is_verified = True
            agent.verification_requested = False
            message = f'Агент {agent.username} успішно верифікований з комісією {commission}%'
        else:
            agent.is_verified = False
            agent.verification_requested = False
            message = f'Запит на верифікацію від агента {agent.username} відхилено'
        
        db.session.commit()
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/agent_details/<int:agent_id>')
@login_required
def admin_agent_details(agent_id):
    """Деталі агента для адміна"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        agent = User.query.get(agent_id)
        if not agent or agent.role != 'agent':
            return jsonify({'success': False, 'message': 'Агент не знайдено'})
        
        # Отримуємо ліди агента
        leads = Lead.query.filter_by(agent_id=agent_id).all()
        
        html = f"""
        <div class="row">
            <div class="col-md-6">
                <h6><i class="fas fa-user"></i> Основна інформація</h6>
                <table class="table table-sm">
                    <tr><td><strong>Ім'я:</strong></td><td>{agent.username}</td></tr>
                    <tr><td><strong>Email:</strong></td><td>{agent.email}</td></tr>
                    <tr><td><strong>Дата реєстрації:</strong></td><td>{agent.created_at.strftime('%d.%m.%Y %H:%M')}</td></tr>
                    <tr><td><strong>Статус верифікації:</strong></td><td>
                        {'<span class="badge bg-success">Верифікований</span>' if agent.is_verified else 
                         '<span class="badge bg-warning">Очікує</span>' if agent.verification_requested else 
                         '<span class="badge bg-secondary">Не верифікований</span>'}
                    </td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6><i class="fas fa-chart-bar"></i> Статистика</h6>
                <table class="table table-sm">
                    <tr><td><strong>Рівень:</strong></td><td>{agent.get_level_display_name()}</td></tr>
                    <tr><td><strong>Поінти:</strong></td><td>{agent.points}</td></tr>
                    <tr><td><strong>Лідів:</strong></td><td>{agent.total_leads}</td></tr>
                    <tr><td><strong>Закритих угод:</strong></td><td>{agent.closed_deals}</td></tr>
                    <tr><td><strong>Комісія:</strong></td><td>{agent.get_commission_rate()}%</td></tr>
                </table>
            </div>
        </div>
        <div class="row mt-3">
            <div class="col-12">
                <h6><i class="fas fa-list"></i> Останні ліди</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Назва угоди</th>
                                <th>Email</th>
                                <th>Статус</th>
                                <th>Дата створення</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for lead in leads[:10]:  # Показуємо тільки останні 10 лідів
            html += f"""
                            <tr>
                                <td>{lead.id}</td>
                                <td>{lead.deal_name}</td>
                                <td>{lead.email}</td>
                                <td><span class="badge bg-{'success' if lead.status == 'closed' else 'primary'}">{lead.status}</span></td>
                                <td>{lead.created_at.strftime('%d.%m.%Y') if lead.created_at else 'Не вказано'}</td>
                            </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
        
        return jsonify({'success': True, 'html': html})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/dashboard_test')
@login_required
def dashboard_test():
    return render_template('dashboard_test.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # ⚡ ОПТИМІЗАЦІЯ: Видалено автоматичну синхронізацію з HubSpot
    # Тепер синхронізація доступна через окрему кнопку
    
    # Імпортуємо необхідні функції для сортування
    from sqlalchemy import func, case
    
    # Отримуємо параметри сортування та пагінації з URL
    sort_by = request.args.get('sort_by', 'updated_at')  # За замовчуванням сортуємо по даті оновлення
    order = request.args.get('order', 'desc')  # За замовчуванням - від нових до старих
    page = request.args.get('page', 1, type=int)  # Номер сторінки
    per_page = 20  # Кількість лідів на сторінку
    
    # Оптимізований запит: отримуємо тільки необхідні ліди
    if current_user.role == 'admin':
        # Адмін бачить свої власні ліди + ліди своїх брокерів
        broker_ids = [broker.id for broker in User.query.filter_by(admin_id=current_user.id, role='agent').all()]
        # Додаємо ID самого адміна до списку
        all_agent_ids = broker_ids + [current_user.id]
        # Якщо немає брокерів, адмін бачить тільки свої ліди
        if all_agent_ids:
            leads_query = Lead.query.filter(Lead.agent_id.in_(all_agent_ids))
        else:
            # Якщо немає брокерів, показуємо всі ліди (для адміна)
            leads_query = Lead.query
    else:
        leads_query = Lead.query.filter_by(agent_id=current_user.id)
    
    # Застосовуємо сортування
    if sort_by == 'status':
        # Для статусу використовуємо custom порядок: new -> contacted -> qualified -> closed
        status_order = case(
            (Lead.status == 'new', 1),
            (Lead.status == 'contacted', 2),
            (Lead.status == 'qualified', 3),
            (Lead.status == 'closed', 4),
            else_=5
        )
        if order == 'asc':
            leads_query = leads_query.order_by(status_order.asc())
        else:
            leads_query = leads_query.order_by(status_order.desc())
    elif sort_by == 'updated_at':
        if order == 'asc':
            leads_query = leads_query.order_by(Lead.updated_at.asc())
        else:
            leads_query = leads_query.order_by(Lead.updated_at.desc())
    
    # Отримуємо ліди з пагінацією
    pagination = leads_query.paginate(page=page, per_page=per_page, error_out=False)
    leads = pagination.items
    
    # ⚡ ОПТИМІЗАЦІЯ: Використовуємо SQL агрегацію замість Python циклів
    # Базовий запит для метрик
    if current_user.role == 'admin':
        # Метрики ТІЛЬКИ для лідів брокерів адміна
        if broker_ids:
            metrics_query = db.session.query(
                func.count(Lead.id).label('total_leads'),
                func.count(case((Lead.status.in_(['new', 'contacted', 'qualified']), 1))).label('active_leads'),
                func.count(case((Lead.status == 'closed', 1))).label('closed_leads'),
                func.count(case((Lead.is_transferred == True, 1))).label('transferred_leads')
            ).filter(Lead.agent_id.in_(broker_ids))
        else:
            # Якщо немає брокерів - нульові метрики
            metrics_query = db.session.query(
                func.count(Lead.id).label('total_leads'),
                func.count(case((Lead.status.in_(['new', 'contacted', 'qualified']), 1))).label('active_leads'),
                func.count(case((Lead.status == 'closed', 1))).label('closed_leads'),
                func.count(case((Lead.is_transferred == True, 1))).label('transferred_leads')
            ).filter(Lead.id == -1)
    else:
        metrics_query = db.session.query(
            func.count(Lead.id).label('total_leads'),
            func.count(case((Lead.status.in_(['new', 'contacted', 'qualified']), 1))).label('active_leads'),
            func.count(case((Lead.status == 'closed', 1))).label('closed_leads'),
            func.count(case((Lead.is_transferred == True, 1))).label('transferred_leads')
        ).filter(Lead.agent_id == current_user.id)
    
    result = metrics_query.first()
    
    total_leads = result.total_leads or 0
    active_leads = result.active_leads or 0
    closed_leads = result.closed_leads or 0
    transferred_leads = result.transferred_leads or 0
    
    # Сума бюджетів (потребує завантаження даних, бо budget - строка)
    total_budget = sum(get_budget_value(lead.budget) for lead in leads)
    avg_budget = total_budget / total_leads if total_leads > 0 else 0
    
    # Конверсія (відсоток закритих лідів)
    conversion_rate = (closed_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Ціль: 10,000 поінтів
    target_points = 10000
    goal_percentage = min(100, (current_user.points / target_points * 100)) if target_points > 0 else 0
    
    metrics = {
        'total_leads': total_leads,
        'active_leads': active_leads,
        'closed_leads': closed_leads,
        'transferred_leads': transferred_leads,
        'total_budget': total_budget,
        'avg_budget': avg_budget,
        'conversion_rate': conversion_rate,
        'goal_percentage': goal_percentage
    }
    
    return render_template('dashboard.html', leads=leads, metrics=metrics, sort_by=sort_by, order=order, pagination=pagination)

@app.route('/add_lead', methods=['GET', 'POST'])
@login_required
def add_lead():
    # Отримуємо всіх користувачів для дропдауна (тільки для адміна)
    all_users = User.query.order_by(User.username).all()
    user_choices = [(user.id, f"{user.username} ({user.role})") for user in all_users]
    
    form = LeadForm(request.form)
    form.agent_id.choices = user_choices
    
    # Встановлюємо agent_id для поточного користувача
    if current_user.role == 'agent':
        form.agent_id.data = current_user.id
    elif current_user.role == 'admin':
        # Для адміна можна вибрати агента, але за замовчуванням - поточний користувач
        if not form.agent_id.data:
            form.agent_id.data = current_user.id
    
    # === ДЕТАЛЬНЕ ЛОГУВАННЯ ДЛЯ ДІАГНОСТИКИ ===
    app.logger.info("=" * 80)
    app.logger.info(f"🔍 ADD_LEAD: Запит методом {request.method}")
    app.logger.info(f"👤 Користувач: {current_user.username} (ID: {current_user.id}, role: {current_user.role})")
    
    if request.method == 'POST':
        app.logger.info(f"📝 Отримані дані форми:")
        for key, value in request.form.items():
            # Не логуємо чутливі дані повністю
            if key in ['email', 'phone']:
                app.logger.info(f"   {key}: {value[:3]}...{value[-3:] if len(value) > 6 else ''}")
            else:
                app.logger.info(f"   {key}: {value}")
        
        # Перевіряємо валідацію форми
        is_valid = form.validate()
        app.logger.info(f"✅ Валідація форми: {'ПРОЙДЕНО' if is_valid else 'ПРОВАЛЕНО'}")
        
        if not is_valid:
            app.logger.error(f"❌ Помилки валідації форми:")
            for field, errors in form.errors.items():
                for error in errors:
                    app.logger.error(f"   {field}: {error}")
                    # Показуємо помилки користувачу
                    flash(f'Помилка поля {field}: {error}', 'error')
    
    if request.method == 'POST' and form.validate():
        app.logger.info("✅ Форма валідна, починаємо обробку...")
        try:
            # Валідація та форматування телефону
            phone_number = form.phone.data
            app.logger.info(f"📞 Валідація номера телефону: {phone_number[:5]}...")
            try:
                parsed_number = phonenumbers.parse(phone_number, None)
                if not phonenumbers.is_valid_number(parsed_number):
                    app.logger.error(f"❌ Невірний формат номера телефону: {phone_number}")
                    flash('Невірний формат номера телефону', 'error')
                    return redirect(url_for('add_lead'))
                formatted_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
                app.logger.info(f"✅ Телефон відформатовано: {formatted_phone}")
            except phonenumbers.NumberParseException as e:
                app.logger.error(f"❌ Помилка парсингу номера: {e}")
                flash('Невірний формат номера телефону', 'error')
                return redirect(url_for('add_lead'))
            
            # ⚡ ОПТИМІЗАЦІЯ: Спочатку зберігаємо лід в локальній БД для швидкості
            # Потім асинхронно синхронізуємо з HubSpot
            
            # Обробка дати народження
            birth_date_obj = None
            if request.form.get('birth_date'):
                try:
                    from datetime import datetime
                    birth_date_obj = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date()
                    app.logger.info(f"📅 Дата народження: {birth_date_obj}")
                except (ValueError, TypeError) as e:
                    app.logger.warning(f"⚠️ Помилка парсингу дати народження: {e}")
                    pass
            
            app.logger.info("💾 Створюємо лід у локальній БД...")
            # Отримуємо agent_id з форми (для адміна може бути вибраний інший агент)
            selected_agent_id = form.agent_id.data if form.agent_id.data else current_user.id
            
            # Створюємо лід локально
            lead = Lead(
                agent_id=selected_agent_id,
                deal_name=form.deal_name.data,
                email=form.email.data,
                phone=formatted_phone,
                budget=form.budget.data,
                notes=form.notes.data,
                second_phone=request.form.get('second_phone', '').strip() or None,
                company=request.form.get('company', '').strip() or None,
                telegram_nickname=request.form.get('telegram_nickname', '').strip() or None,
                messenger=request.form.get('messenger', '').strip() or None,
                birth_date=birth_date_obj,
                hubspot_contact_id=None,
                hubspot_deal_id=None
            )
            
            db.session.add(lead)
            app.logger.info(f"✅ Лід додано до сесії БД")
            
            # Нараховуємо поінти за створення ліда
            agent = User.query.get(selected_agent_id)
            if agent:
                app.logger.info(f"🎯 Нараховуємо 100 поінтів агенту {agent.username}")
                agent.add_points(100)  # 100 поінтів за лід
                agent.total_leads += 1
            
            # Комітимо зміни в БД ПЕРЕД HubSpot викликами
            app.logger.info("💾 Комітимо зміни в БД...")
            db.session.commit()
            app.logger.info(f"✅ Лід #{lead.id} успішно збережено в локальній БД!")
            
            # Ініціалізуємо HubSpot ID як None
            hubspot_contact_id = None
            hubspot_deal_id = None
            hubspot_sync_success = False
            
            # Тепер пробуємо синхронізувати з HubSpot (не блокує відповідь при помилці)
            if hubspot_client:
                print(f"=== ПОЧАТОК СТВОРЕННЯ КОНТАКТУ В HUBSPOT ===")
                print(f"Email: {form.email.data}")
                print(f"Deal name: {form.deal_name.data}")
                print(f"Phone: {formatted_phone}")
                print(f"Budget: {form.budget.data}")
                print(f"HubSpot client: {hubspot_client}")
                try:
                    # Перевіряємо, чи існує контакт з таким email
                    from hubspot.crm.contacts import SimplePublicObjectInput
                    
                    try:
                        # Шукаємо існуючий контакт за email (якщо він вказаний)
                        print(f"=== ПОШУК ІСНУЮЧОГО КОНТАКТУ ===")
                        from hubspot.crm.contacts import PublicObjectSearchRequest
                        
                        existing_contacts = None
                        if form.email.data and form.email.data.strip():
                            print(f"Пошук за email: {form.email.data}")
                            search_request = PublicObjectSearchRequest(
                                query=form.email.data,
                                properties=["email", "firstname", "lastname"],
                                limit=1
                            )
                            existing_contacts = hubspot_client.crm.contacts.search_api.do_search(
                                public_object_search_request=search_request
                            )
                            print(f"Пошук контакту за email {form.email.data}: знайдено {len(existing_contacts.results)} контактів")
                            if existing_contacts.results:
                                print(f"Знайдений контакт: ID={existing_contacts.results[0].id}, properties={existing_contacts.results[0].properties}")
                        else:
                            print(f"Email не вказано, створюємо контакт тільки з телефоном")
                        
                        if existing_contacts and existing_contacts.results:
                            # Контакт існує, використовуємо його
                            hubspot_contact_id = str(existing_contacts.results[0].id)
                            print(f"Використовуємо існуючий HubSpot контакт: {hubspot_contact_id}")
                        else:
                            # Контакт не існує, створюємо новий
                            print(f"=== СТВОРЕННЯ НОВОГО КОНТАКТУ ===")
                            print(f"Контакт не знайдено, створюємо новий")
                            contact_properties = {
                                "phone": formatted_phone,
                                "firstname": form.deal_name.data.split()[0] if form.deal_name.data.split() else "Lead",
                                "lastname": " ".join(form.deal_name.data.split()[1:]) if len(form.deal_name.data.split()) > 1 else "Client"
                            }
                            
                            # Додаємо email тільки якщо він заповнений
                            if form.email.data and form.email.data.strip():
                                contact_properties["email"] = form.email.data.strip()
                            
                            # Додаємо додаткові поля, якщо вони заповнені
                            if request.form.get('second_phone', '').strip():
                                contact_properties["phone_number_1"] = request.form.get('second_phone').strip()
                            if request.form.get('company', '').strip():
                                contact_properties["company"] = request.form.get('company').strip()
                            if request.form.get('telegram_nickname', '').strip():
                                contact_properties["telegram"] = request.form.get('telegram_nickname').strip()
                            if request.form.get('messenger', '').strip():
                                contact_properties["messenger"] = request.form.get('messenger').strip()
                            if request.form.get('birth_date', '').strip():
                                contact_properties["birthdate"] = request.form.get('birth_date').strip()
                            
                            contact_input = SimplePublicObjectInput(properties=contact_properties)
                            hubspot_contact = hubspot_client.crm.contacts.basic_api.create(contact_input)
                            hubspot_contact_id = str(hubspot_contact.id)
                            print(f"HubSpot контакт створено: {hubspot_contact_id}")
                            
                    except Exception as search_error:
                        print(f"=== ПОМИЛКА ПОШУКУ КОНТАКТУ ===")
                        print(f"Помилка пошуку контакту: {search_error}")
                        print(f"Тип помилки: {type(search_error).__name__}")
                        print(f"Email: {form.email.data}")
                        traceback.print_exc()
                        # Якщо пошук не вдався, спробуємо створити контакт
                        try:
                            contact_properties = {
                                "phone": formatted_phone,
                                "firstname": form.deal_name.data.split()[0] if form.deal_name.data.split() else "Lead",
                                "lastname": " ".join(form.deal_name.data.split()[1:]) if len(form.deal_name.data.split()) > 1 else "Client"
                            }
                            
                            # Додаємо email тільки якщо він заповнений
                            if form.email.data and form.email.data.strip():
                                contact_properties["email"] = form.email.data.strip()
                            
                            # Додаємо додаткові поля, якщо вони заповнені
                            if request.form.get('second_phone', '').strip():
                                contact_properties["phone_number_1"] = request.form.get('second_phone').strip()
                            if request.form.get('company', '').strip():
                                contact_properties["company"] = request.form.get('company').strip()
                            if request.form.get('telegram_nickname', '').strip():
                                contact_properties["telegram"] = request.form.get('telegram_nickname').strip()
                            if request.form.get('messenger', '').strip():
                                contact_properties["messenger"] = request.form.get('messenger').strip()
                            if request.form.get('birth_date', '').strip():
                                contact_properties["birthdate"] = request.form.get('birth_date').strip()
                            
                            contact_input = SimplePublicObjectInput(properties=contact_properties)
                            hubspot_contact = hubspot_client.crm.contacts.basic_api.create(contact_input)
                            hubspot_contact_id = str(hubspot_contact.id)
                            print(f"HubSpot контакт створено: {hubspot_contact_id}")
                        except Exception as create_error:
                            print(f"=== ПОМИЛКА СТВОРЕННЯ КОНТАКТУ ===")
                            print(f"Помилка створення контакту: {create_error}")
                            print(f"Тип помилки: {type(create_error).__name__}")
                            print(f"Email: {form.email.data}")
                            print(f"Phone: {formatted_phone}")
                            traceback.print_exc()
                            # Логуємо помилку, але продовжуємо роботу (лід вже збережений в БД)
                            app.logger.warning(f"⚠️ Помилка створення HubSpot контакту: {create_error}")
                            # Не прокидаємо помилку далі - лід вже збережений локально
                    
                    # Створюємо deal в HubSpot (тільки якщо контакт створений)
                    if hubspot_contact_id:
                        print(f"=== СТВОРЕННЯ УГОДИ В HUBSPOT ===")
                        print(f"Створюємо угоду в HubSpot: {form.deal_name.data}")
                        print(f"Контакт ID: {hubspot_contact_id}")
                        try:
                            from hubspot.crm.deals import SimplePublicObjectInput as DealInput
                            
                            # Отримуємо HubSpot owner ID для агента
                            hubspot_owner_id = None
                            agent = User.query.get(form.agent_id.data) if form.agent_id.data else current_user
                            if agent and hubspot_client:
                                try:
                                    # Шукаємо owner в HubSpot по email агента
                                    print(f"🔍 Пошук HubSpot owner для агента: {agent.email}")
                                    owners = hubspot_client.crm.owners.owners_api.get_page()
                                    for owner in owners.results:
                                        if owner.email and owner.email.lower() == agent.email.lower():
                                            hubspot_owner_id = str(owner.id)
                                            print(f"✅ Знайдено HubSpot owner ID: {hubspot_owner_id} для {agent.email}")
                                            break
                                    if not hubspot_owner_id:
                                        print(f"⚠️ HubSpot owner не знайдено для {agent.email}")
                                except Exception as owner_error:
                                    print(f"⚠️ Помилка пошуку HubSpot owner: {owner_error}")
                                    app.logger.warning(f"⚠️ Помилка пошуку HubSpot owner для {agent.email}: {owner_error}")
                            
                            # Отримуємо username вибраного агента (може бути інший агент, якщо адмін вибрав)
                            selected_agent = User.query.get(selected_agent_id) if selected_agent_id else current_user
                            agent_username = selected_agent.username if selected_agent else current_user.username
                            
                            # Використовуємо pipeline "default" з stage "appointmentscheduled"
                            # Згідно з HubSpot API: pipeline ID = "default", stage ID = "appointmentscheduled"
                            deal_properties = {
                                "dealname": form.deal_name.data,
                                "amount": get_budget_value(form.budget.data),
                                "dealtype": "newbusiness",
                                "pipeline": "default",  # Pipeline ID для "Лиды" (default pipeline)
                                "dealstage": "appointmentscheduled",  # Стадія ID для "Новая заявка"
                                "phone_number": formatted_phone,  # Додаємо номер телефону в угоду
                                "from_agent_portal__name_": agent_username  # Ім'я агента (обробника), який відповідає за лід
                            }
                            print(f"✅ Використовуємо pipeline: default, stage: appointmentscheduled")
                            
                            # Додаємо hubspot_owner_id якщо знайдено
                            if hubspot_owner_id:
                                deal_properties["hubspot_owner_id"] = hubspot_owner_id
                                print(f"✅ Додано hubspot_owner_id: {hubspot_owner_id} до угоди")
                            else:
                                print(f"⚠️ hubspot_owner_id не встановлено (owner не знайдено або не налаштовано)")
                            
                            print(f"Властивості угоди: {deal_properties}")
                            deal_input = DealInput(properties=deal_properties)
                            print(f"Створюємо угоду з вхідними даними: {deal_input}")
                            hubspot_deal = hubspot_client.crm.deals.basic_api.create(deal_input)
                            hubspot_deal_id = str(hubspot_deal.id)
                            print(f"HubSpot угода створено успішно: {hubspot_deal_id}")
                            
                            # Створюємо зв'язок між контактом та угодою
                            print(f"=== СТВОРЕННЯ ЗВ'ЯЗКУ КОНТАКТ-УГОДА ===")
                            try:
                                hubspot_client.crm.associations.basic_api.create(
                                    from_object_type="contacts",
                                    from_object_id=hubspot_contact_id,
                                    to_object_type="deals", 
                                    to_object_id=hubspot_deal_id,
                                    association_type="contact_to_deal"
                                )
                                print(f"Зв'язок між контактом {hubspot_contact_id} та угодою {hubspot_deal_id} створено")
                            except Exception as assoc_error:
                                print(f"=== ПОМИЛКА СТВОРЕННЯ ЗВ'ЯЗКУ ===")
                                print(f"Помилка створення зв'язку: {assoc_error}")
                                print(f"Тип помилки: {type(assoc_error).__name__}")
                                app.logger.warning(f"⚠️ Помилка створення зв'язку HubSpot: {assoc_error}")
                                # Не критична помилка - продовжуємо
                        except Exception as deal_error:
                            print(f"=== ПОМИЛКА СТВОРЕННЯ УГОДИ ===")
                            print(f"Помилка створення угоди: {deal_error}")
                            app.logger.warning(f"⚠️ Помилка створення HubSpot угоди: {deal_error}")
                            # Не критична помилка - контакт вже створений, продовжуємо
                    else:
                        print("⚠️ HubSpot контакт не створений, пропускаємо створення угоди")
                    
                    # Визначаємо успішність синхронізації
                    if hubspot_contact_id:
                        hubspot_sync_success = True
                        print(f"✅ HubSpot синхронізація успішна! Contact: {hubspot_contact_id}, Deal: {hubspot_deal_id if hubspot_deal_id else 'не створено'}")
                    else:
                        hubspot_sync_success = False
                        print("⚠️ HubSpot синхронізація не виконана (контакт не створений)")
                    
                except Exception as hubspot_error:
                    error_msg = str(hubspot_error)
                    print(f"=== ДЕТАЛЬНА ПОМИЛКА HUBSPOT ===")
                    print(f"Тип помилки: {type(hubspot_error).__name__}")
                    print(f"Повідомлення: {error_msg}")
                    print(f"Email: {form.email.data}")
                    print(f"Deal name: {form.deal_name.data}")
                    print(f"Phone: {formatted_phone}")
                    print(f"Budget: {form.budget.data}")
                    traceback.print_exc()
                    
                    # Логуємо в файл
                    app.logger.error(f"HubSpot помилка при створенні ліда: {error_msg}")
                    app.logger.error(f"Деталі: email={form.email.data}, deal_name={form.deal_name.data}, phone={formatted_phone}")
                    
                    # Логуємо помилку, але не блокуємо успішне створення ліда
                    # Лід вже збережений в локальній БД, тому просто додаємо повідомлення
                    if "Contact already exists" in error_msg or "409" in error_msg:
                        flash(f'Лід додано локально. Контакт з email {form.email.data} вже існує в HubSpot.', 'warning')
                    elif "401" in error_msg or "Unauthorized" in error_msg:
                        flash('Лід додано локально. Помилка авторизації HubSpot API (недійсний ключ).', 'warning')
                    elif "403" in error_msg or "Forbidden" in error_msg:
                        flash('Лід додано локально. Немає прав доступу до HubSpot API.', 'warning')
                    elif "429" in error_msg or "rate limit" in error_msg.lower():
                        flash('Лід додано локально. Перевищено ліміт запитів до HubSpot API.', 'warning')
                    else:
                        flash(f'Лід додано локально. Помилка HubSpot: {error_msg[:100]}...', 'warning')
                    # Продовжуємо виконання - лід вже збережений, просто без HubSpot синхронізації
            else:
                print("HubSpot клієнт не налаштований")
            
            # ⚡ ОПТИМІЗАЦІЯ: Оновлюємо лід з HubSpot ID, якщо синхронізація успішна
            if hubspot_contact_id or hubspot_deal_id:
                lead.hubspot_contact_id = hubspot_contact_id
                lead.hubspot_deal_id = hubspot_deal_id
                db.session.commit()
                print(f"Лід #{lead.id} оновлено з HubSpot ID: contact={hubspot_contact_id}, deal={hubspot_deal_id}")
            
            # Повертаємо відповідь користувачу
            if hubspot_sync_success and hubspot_contact_id:
                app.logger.info(f"🎉 УСПІХ! Лід #{lead.id} додано локально та синхронізовано з HubSpot!")
                app.logger.info(f"   HubSpot Contact ID: {hubspot_contact_id}")
                app.logger.info(f"   HubSpot Deal ID: {hubspot_deal_id}")
                flash('Лід успішно додано та синхронізовано з HubSpot!', 'success')
            else:
                app.logger.info(f"🎉 УСПІХ! Лід #{lead.id} додано локально!")
                app.logger.warning(f"⚠️ HubSpot синхронізація не виконана або часткова")
                flash('Лід успішно додано локально!', 'success')
            
            app.logger.info("🔄 Перенаправлення на dashboard...")
            app.logger.info("=" * 80)
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            app.logger.error("=" * 80)
            app.logger.error(f"❌❌❌ КРИТИЧНА ПОМИЛКА при додаванні ліда!")
            app.logger.error(f"Тип помилки: {type(e).__name__}")
            app.logger.error(f"Повідомлення: {str(e)}")
            app.logger.error(f"Stack trace:\n{traceback.format_exc()}")
            app.logger.error("=" * 80)
            
            flash(f'Помилка при додаванні ліда: {str(e)}', 'error')
            return redirect(url_for('add_lead'))
    
    # GET запит або невалідна форма
    if request.method == 'POST':
        app.logger.warning("⚠️ POST запит, але форма не пройшла валідацію")
    else:
        app.logger.info("📄 GET запит - відображаємо форму")
    
    app.logger.info("=" * 80)
    return render_template('add_lead.html', form=form)

@app.route('/update_status/<int:lead_id>', methods=['POST'])
@login_required
def update_status(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        flash('У вас немає прав для редагування цього ліда')
        return redirect(url_for('dashboard'))
    
    new_status = request.json.get('status')
    if new_status:
        lead.status = new_status
        db.session.commit()
        
        # Оновлюємо статус в HubSpot (якщо є ID)
        if lead.hubspot_contact_id:
            try:
                from hubspot.crm.contacts import SimplePublicObjectInput
                
                contact_properties = {"hs_lead_status": new_status.upper()}
                contact_input = SimplePublicObjectInput(properties=contact_properties)
                
                hubspot_client.crm.contacts.basic_api.update(
                    contact_id=lead.hubspot_contact_id,
                    simple_public_object_input=contact_input
                )
            except Exception as e:
                print(f"Помилка оновлення HubSpot: {e}")
        
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/transfer_lead/<int:lead_id>', methods=['POST'])
@login_required
def transfer_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для редагування цього ліда'})
    
    # Переключаємо статус передачі
    lead.is_transferred = not lead.is_transferred
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'is_transferred': lead.is_transferred,
        'message': 'Лід позначено як переданий' if lead.is_transferred else 'Лід позначено як не переданий'
    })


# ==================== COMMENT/COMMENTS API ====================

@app.route('/api/leads/<int:lead_id>/comments', methods=['GET'])
@login_required
def get_lead_comments(lead_id):
    """Отримати всі коментарі для ліда (threaded structure)"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Перевірка прав доступу
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для перегляду цього ліда'}), 403
    
    try:
        # Отримуємо всі коментарі для ліда
        all_comments = Comment.query.filter_by(lead_id=lead_id).order_by(Comment.created_at.asc()).all()
        
        # Створюємо структуру для threaded comments
        comments_dict = {}
        root_comments = []
        
        for comment in all_comments:
            comment_data = comment.to_dict()
            comment_data['replies'] = []
            comments_dict[comment.id] = comment_data
            
            if comment.parent_id is None:
                # Це кореневий коментар
                root_comments.append(comment_data)
            else:
                # Це відповідь - додаємо до батьківського коментаря
                if comment.parent_id in comments_dict:
                    comments_dict[comment.parent_id]['replies'].append(comment_data)
        
        return jsonify({
            'success': True,
            'comments': root_comments,
            'total_count': len(all_comments)
        })
    except Exception as e:
        app.logger.error(f"Помилка отримання коментарів: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'}), 500

@app.route('/api/leads/<int:lead_id>/comments', methods=['POST'])
@login_required
def create_lead_comment(lead_id):
    """Створити новий коментар для ліда"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Перевірка прав доступу
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для коментування цього ліда'}), 403
    
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')  # ID батьківського коментаря (для відповіді)
        
        app.logger.info(f"📝 Створення коментаря для ліда {lead_id}")
        app.logger.info(f"   Content: {content[:100]}...")
        app.logger.info(f"   Parent ID: {parent_id}")
        
        if not content:
            return jsonify({'success': False, 'message': 'Текст коментаря не може бути порожнім'}), 400
        
        # Перевірка, чи існує батьківський коментар (якщо вказано)
        parent_comment = None
        if parent_id:
            parent_comment = Comment.query.filter_by(id=parent_id, lead_id=lead_id).first()
            if not parent_comment:
                app.logger.warning(f"⚠️ Батьківський коментар {parent_id} не знайдено для ліда {lead_id}")
                return jsonify({'success': False, 'message': 'Батьківський коментар не знайдено'}), 404
            app.logger.info(f"✅ Знайдено батьківський коментар: {parent_comment.id} - {parent_comment.content[:50]}...")
        
        # Створюємо коментар
        comment = Comment(
            lead_id=lead_id,
            user_id=current_user.id,
            parent_id=parent_id,
            content=content
        )
        db.session.add(comment)
        db.session.flush()  # Отримуємо ID коментаря
        
        # Створюємо нотатку в HubSpot (якщо є deal_id)
        if lead.hubspot_deal_id and hubspot_client:
            try:
                from hubspot.crm.objects.notes import SimplePublicObjectInput
                from datetime import datetime, timezone
                
                # Формуємо текст нотатки з інформацією про автора
                if parent_id and parent_comment:
                    # Для відповіді додаємо інформацію про батьківський коментар
                    parent_author = parent_comment.user.username if parent_comment.user else "Unknown"
                    parent_content = parent_comment.content[:100] + ("..." if len(parent_comment.content) > 100 else "")
                    note_body = f"Відповідь на коментар від {parent_author}:\n\"{parent_content}\"\n\n[{current_user.username}]: {content}"
                    app.logger.info(f"📝 Створюється нотатка-відповідь на коментар {parent_id}")
                else:
                    note_body = f"[{current_user.username}]: {content}"
                    app.logger.info(f"📝 Створюється нова нотатка")
                
                # HubSpot вимагає hs_timestamp в форматі ISO8601
                current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                
                # Використовуємо правильну назву поля: hsnotebody (без підкреслення)
                # Спробуємо створити нотатку через прямий HTTP запит для кращого контролю
                import requests
                api_key = HUBSPOT_API_KEY
                
                # Створюємо нотатку через v3 API
                url = "https://api.hubapi.com/crm/v3/objects/notes"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Тіло запиту з асоціацією до deal
                # Правильна назва поля: hs_note_body (з підкресленням), не hsnotebody
                data = {
                    "properties": {
                        "hs_note_body": note_body,  # Правильна назва поля
                        "hs_timestamp": current_timestamp
                    },
                    "associations": [{
                        "to": {
                            "id": lead.hubspot_deal_id
                        },
                        "types": [{
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 214  # Для notes-deals
                        }]
                    }]
                }
                
                app.logger.info(f"📝 Створення нотатки в HubSpot для deal {lead.hubspot_deal_id}")
                app.logger.info(f"   Тіло запиту: {data}")
                
                response = requests.post(url, headers=headers, json=data)
                
                app.logger.info(f"📥 Відповідь HubSpot API: {response.status_code}")
                app.logger.info(f"   Response body: {response.text[:500] if response.text else 'Empty'}")
                
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    hubspot_note_id = response_data.get('id')
                    if hubspot_note_id:
                        comment.hubspot_note_id = str(hubspot_note_id)
                        app.logger.info(f"✅ Нотатка створена та асоційована з deal в HubSpot: {hubspot_note_id}")
                        print(f"✅ Нотатка створена та асоційована з deal в HubSpot: {hubspot_note_id}")
                        
                        # Додатково перевіряємо, чи асоціація дійсно створена
                        # Інколи асоціація в одному запиті не працює, робимо окремий запит
                        try:
                            assoc_url = f"https://api.hubapi.com/crm/v4/objects/notes/{hubspot_note_id}/associations/deal/{lead.hubspot_deal_id}"
                            assoc_data = [{
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 214
                            }]
                            assoc_response = requests.put(assoc_url, headers=headers, json=assoc_data)
                            if assoc_response.status_code in [200, 201]:
                                app.logger.info(f"✅ Асоціація підтверджена через окремий запит")
                            else:
                                app.logger.warning(f"⚠️ Асоціація не підтверджена: {assoc_response.status_code} - {assoc_response.text}")
                        except Exception as assoc_check_error:
                            app.logger.warning(f"⚠️ Помилка перевірки асоціації: {assoc_check_error}")
                    else:
                        app.logger.warning(f"⚠️ Нотатка створена, але ID не отримано: {response_data}")
                        print(f"⚠️ Нотатка створена, але ID не отримано")
                else:
                    # Якщо HTTP запит не працює, спробуємо через SDK як fallback
                    app.logger.warning(f"⚠️ HTTP запит не вдався ({response.status_code}), спробуємо через SDK: {response.text}")
                    print(f"⚠️ HTTP запит не вдався, спробуємо через SDK...")
                    
                    # Fallback через SDK
                    note_properties = {
                        "hs_note_body": note_body,  # Правильна назва поля
                        "hs_timestamp": current_timestamp
                    }
                    note_input = SimplePublicObjectInput(properties=note_properties)
                    hubspot_note = hubspot_client.crm.objects.notes.basic_api.create(
                        simple_public_object_input=note_input
                    )
                    
                    if hubspot_note.id:
                        comment.hubspot_note_id = str(hubspot_note.id)
                        
                        # Асоціюємо через окремий запит
                        try:
                            url = f"https://api.hubapi.com/crm/v4/objects/notes/{hubspot_note.id}/associations/deal/{lead.hubspot_deal_id}"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            }
                            data = [{
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 214
                            }]
                            
                            assoc_response = requests.put(url, headers=headers, json=data)
                            if assoc_response.status_code in [200, 201]:
                                print(f"✅ Нотатка створена та асоційована з deal (fallback) в HubSpot: {hubspot_note.id}")
                            else:
                                app.logger.warning(f"⚠️ Асоціація не вдалася: {assoc_response.status_code} - {assoc_response.text}")
                        except Exception as assoc_error:
                            app.logger.warning(f"⚠️ Помилка асоціації: {assoc_error}")
                    
            except Exception as hubspot_error:
                app.logger.error(f"❌ Помилка створення нотатки в HubSpot: {hubspot_error}")
                app.logger.error(f"   Тип помилки: {type(hubspot_error).__name__}")
                import traceback
                app.logger.error(f"   Traceback: {traceback.format_exc()}")
                print(f"❌ Помилка створення нотатки в HubSpot: {hubspot_error}")
                # Продовжуємо - коментар все одно зберігається локально
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': comment.to_dict(),
            'message': 'Коментар успішно створено'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка створення коментаря: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'}), 500

@app.route('/api/comments/<int:comment_id>', methods=['PUT'])
@login_required
def update_comment(comment_id):
    """Оновити коментар"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Перевірка прав доступу (тільки автор або адмін)
    if comment.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для редагування цього коментаря'}), 403
    
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'message': 'Текст коментаря не може бути порожнім'}), 400
        
        comment.content = content
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': comment.to_dict(),
            'message': 'Коментар успішно оновлено'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка оновлення коментаря: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'}), 500

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Видалити коментар"""
    comment = Comment.query.get_or_404(comment_id)
    
    # Перевірка прав доступу (тільки автор або адмін)
    if comment.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для видалення цього коментаря'}), 403
    
    try:
        # Видаляємо нотатку з HubSpot (якщо є)
        if comment.hubspot_note_id and hubspot_client:
            try:
                hubspot_client.crm.objects.notes.basic_api.archive(
                    object_id=comment.hubspot_note_id
                )
                print(f"✅ Нотатка видалена з HubSpot: {comment.hubspot_note_id}")
            except Exception as hubspot_error:
                app.logger.warning(f"⚠️ Помилка видалення нотатки з HubSpot: {hubspot_error}")
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Коментар успішно видалено'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка видалення коментаря: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'}), 500

@app.route('/lead/<int:lead_id>')
@login_required
def view_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        flash('У вас немає прав для перегляду цього ліда')
        return redirect(url_for('dashboard'))
    
    # Синхронізація тепер відбувається автоматично у фоні кожні 60 секунд
    # Для ручного оновлення є кнопка "Оновити" на сторінці
    
    agent = User.query.get(lead.agent_id)
    notes = []  # Нотатки видалені з системи
    
    try:
        activities = Activity.query.filter_by(lead_id=lead.id).order_by(Activity.created_at.desc()).all()
    except Exception:
        # Якщо таблиця activity не існує, використовуємо порожній список
        activities = []
    
    from datetime import date
    return render_template('lead_detail.html', lead=lead, agent=agent, notes=notes, activities=activities, today=date.today())

@app.route('/lead/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        flash('У вас немає прав для редагування цього ліда')
        return redirect(url_for('dashboard'))
    
    form = LeadEditForm(request.form)
    
    if request.method == 'GET':
        # Заповнюємо форму поточними даними
        form.deal_name.data = lead.deal_name
        form.email.data = lead.email
        form.phone.data = lead.phone
        form.budget.data = lead.budget
        form.status.data = lead.status
        form.country.data = lead.country
        form.purchase_goal.data = lead.purchase_goal
        form.property_type.data = lead.property_type
        form.object_type.data = lead.object_type
        form.communication_language.data = lead.communication_language
        form.source.data = lead.source
        form.refusal_reason.data = lead.refusal_reason
        form.company.data = lead.company
        form.second_phone.data = lead.second_phone
        form.telegram_nickname.data = lead.telegram_nickname
        form.messenger.data = lead.messenger
        form.birth_date.data = lead.birth_date.strftime('%Y-%m-%d') if lead.birth_date else ''
    
    if request.method == 'POST' and form.validate():
        # Зберігаємо старий статус для порівняння
        old_status = lead.status
        
        # Оновлюємо дані ліда
        lead.deal_name = form.deal_name.data
        lead.email = form.email.data
        lead.phone = form.phone.data
        lead.budget = form.budget.data
        lead.status = form.status.data
        lead.country = form.country.data
        lead.purchase_goal = form.purchase_goal.data
        lead.property_type = form.property_type.data
        lead.object_type = form.object_type.data
        lead.communication_language = form.communication_language.data
        lead.source = form.source.data
        lead.refusal_reason = form.refusal_reason.data
        lead.company = form.company.data
        lead.second_phone = form.second_phone.data
        lead.telegram_nickname = form.telegram_nickname.data
        lead.messenger = form.messenger.data
        
        # Обробка дати народження
        if form.birth_date.data:
            try:
                from datetime import datetime
                lead.birth_date = datetime.strptime(form.birth_date.data, '%Y-%m-%d').date()
            except ValueError:
                flash('Невірний формат дати народження')
                return render_template('edit_lead.html', form=form, lead=lead)
        else:
            lead.birth_date = None
        
        db.session.commit()
        
        # Якщо статус змінився, оновлюємо його в HubSpot
        if old_status != lead.status:
            print(f"🔄 Статус змінився з '{old_status}' на '{lead.status}', оновлюємо HubSpot...")
            app.logger.info(f"🔄 Статус ліда {lead.id} змінився з '{old_status}' на '{lead.status}', оновлюємо HubSpot...")
            
            if update_hubspot_dealstage(lead, lead.status):
                flash(f'Лід успішно оновлено! Статус синхронізовано з HubSpot.', 'success')
            else:
                flash(f'Лід оновлено локально, але статус не було синхронізовано з HubSpot.', 'warning')
        else:
            flash('Лід успішно оновлено!', 'success')
        
        return redirect(url_for('view_lead', lead_id=lead.id))
    
    return render_template('edit_lead.html', form=form, lead=lead)

@app.route('/sync_lead/<int:lead_id>', methods=['POST'])
@login_required
def sync_lead(lead_id):
    """Ручна синхронізація конкретного ліда з HubSpot"""
    lead = Lead.query.get_or_404(lead_id)
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для синхронізації цього ліда'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        success = sync_lead_from_hubspot(lead)
        if success:
            return jsonify({'success': True, 'message': 'Лід успішно синхронізовано з HubSpot'})
        else:
            return jsonify({'success': False, 'message': 'Помилка синхронізації з HubSpot'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/sync_all_leads', methods=['POST'])
@login_required
def sync_all_leads():
    """Ручна синхронізація всіх лідів з HubSpot (оновлення існуючих)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Тільки адміністратор може синхронізувати всі ліді'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        success = sync_all_leads_from_hubspot()
        if success:
            return jsonify({'success': True, 'message': 'Всі ліди успішно синхронізовано з HubSpot'})
        else:
            return jsonify({'success': False, 'message': 'Помилка синхронізації з HubSpot'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/fetch_all_deals', methods=['POST'])
@login_required
def fetch_all_deals():
    """Ручне завантаження всіх deals з HubSpot та створення/оновлення ліди в локальній БД"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Тільки адміністратор може завантажувати всі deals'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        result = fetch_all_deals_from_hubspot()
        return jsonify({
            'success': True,
            'message': f'Завантажено: створено {result.get("created", 0)}, оновлено {result.get("updated", 0)}, помилок {result.get("errors", 0)}',
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
            'errors': result.get('errors', 0),
            'total_processed': result.get('total_processed', 0)
        })
    except Exception as e:
        app.logger.error(f"Помилка завантаження deals: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/fetch_all_contacts', methods=['POST'])
@login_required
def fetch_all_contacts():
    """Ручне завантаження всіх контактів з HubSpot CRM та створення/оновлення ліди в локальній БД"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Тільки адміністратор може завантажувати всі контакти'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        result = fetch_all_contacts_from_hubspot()
        return jsonify({
            'success': True,
            'message': f'Завантажено: створено {result.get("created", 0)}, оновлено {result.get("updated", 0)}, помилок {result.get("errors", 0)}',
            'created': result.get('created', 0),
            'updated': result.get('updated', 0),
            'errors': result.get('errors', 0),
            'total_processed': result.get('total_processed', 0)
        })
    except Exception as e:
        app.logger.error(f"Помилка завантаження контактів: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/sync_lead/<int:lead_id>', methods=['POST'])
@login_required
def sync_single_lead(lead_id):
    """Ручна синхронізація окремого ліда з HubSpot"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Перевірка прав доступу
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для синхронізації цього ліда'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        success = sync_lead_from_hubspot(lead)
        if success:
            from datetime import datetime
            # Форматуємо час останньої синхронізації
            if lead.last_sync_at:
                last_sync = lead.last_sync_at.strftime('%d.%m.%Y %H:%M')
            else:
                last_sync = 'Невідомо'
            
            return jsonify({
                'success': True, 
                'message': 'Лід успішно синхронізовано з HubSpot',
                'last_sync_at': last_sync
            })
        else:
            return jsonify({'success': False, 'message': 'Помилка синхронізації з HubSpot'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/knowledge-base')
@login_required
def knowledge_base():
    """Сторінка Knowledge Base - показує модалку 'to be soon'"""
    return render_template('knowledge_base.html')

@app.route('/admin/hubspot-contacts')
@login_required
def admin_hubspot_contacts():
    """Сторінка з усіма номерами телефонів з HubSpot CRM"""
    if current_user.role != 'admin':
        flash('Доступ заборонено')
        return redirect(url_for('dashboard'))
    
    if not hubspot_client:
        flash('HubSpot API не налаштований', 'error')
        return redirect(url_for('dashboard'))
    
    contacts_data = []
    
    try:
        print("🔄 Завантаження всіх контактів з HubSpot...")
        app.logger.info("🔄 Завантаження всіх контактів з HubSpot...")
        
        # Отримуємо всі контакти з HubSpot (посторінково)
        after = None
        page = 0
        max_pages = 1000  # Збільшено для завантаження всіх контактів
        
        while page < max_pages:
            try:
                # Властивості, які потрібні для контактів
                properties = [
                    'phone', 'phone_number', 'mobilephone', 'hs_phone_number',
                    'phone_number_1', 'email', 'firstname', 'lastname'
                ]
                
                # Отримуємо сторінку контактів
                if after:
                    contacts_response = hubspot_client.crm.contacts.basic_api.get_page(
                        limit=100,
                        after=after,
                        properties=properties
                    )
                else:
                    contacts_response = hubspot_client.crm.contacts.basic_api.get_page(
                        limit=100,
                        properties=properties
                    )
                
                if not contacts_response.results:
                    break
                
                print(f"📄 Сторінка {page + 1}: отримано {len(contacts_response.results)} контактів")
                
                # Обробляємо кожен контакт
                for contact in contacts_response.results:
                    contact_id = str(contact.id)
                    
                    # Отримуємо всі номери телефонів з контакту
                    phone_numbers = []
                    
                    # Перевіряємо всі можливі поля телефонів
                    for phone_field in ['phone', 'phone_number', 'mobilephone', 'hs_phone_number', 'phone_number_1']:
                        phone_value = contact.properties.get(phone_field)
                        if phone_value:
                            phone_numbers.append(phone_value)
                    
                    # Якщо є номери, додаємо контакт до списку
                    if phone_numbers:
                        # Об'єднуємо всі номери в один рядок
                        phones_str = ', '.join(phone_numbers)
                        
                        contacts_data.append({
                            'id': contact_id,
                            'phone': phones_str,
                            'email': contact.properties.get('email', ''),
                            'name': f"{contact.properties.get('firstname', '')} {contact.properties.get('lastname', '')}".strip() or 'Без імені'
                        })
                
                # Перевіряємо, чи є ще сторінки
                if not contacts_response.paging or not contacts_response.paging.next:
                    break
                
                after = contacts_response.paging.next.after
                page += 1
                
                # Додаємо затримку між сторінками для rate limiting
                time.sleep(0.5)
                
            except Exception as page_error:
                print(f"❌ Помилка отримання сторінки {page + 1}: {page_error}")
                app.logger.error(f"❌ Помилка отримання сторінки {page + 1}: {page_error}")
                break
        
        print(f"✅ Завантажено {len(contacts_data)} контактів з номерами телефонів")
        app.logger.info(f"✅ Завантажено {len(contacts_data)} контактів з номерами телефонів")
        
    except Exception as e:
        print(f"❌ Критична помилка при завантаженні контактів з HubSpot: {e}")
        app.logger.error(f"❌ Критична помилка при завантаженні контактів з HubSpot: {e}")
        traceback.print_exc()
        flash(f'Помилка завантаження контактів: {str(e)}', 'error')
    
    return render_template('admin_hubspot_contacts.html', contacts=contacts_data)

@app.route('/admin/hubspot-contacts/export-csv')
@login_required
def admin_hubspot_contacts_export_csv():
    """Експорт всіх номерів телефонів з HubSpot CRM в CSV файл"""
    if current_user.role != 'admin':
        flash('Доступ заборонено')
        return redirect(url_for('dashboard'))
    
    if not hubspot_client:
        flash('HubSpot API не налаштований', 'error')
        return redirect(url_for('dashboard'))
    
    import csv
    from io import StringIO
    
    contacts_data = []
    
    try:
        print("🔄 Завантаження всіх контактів з HubSpot для експорту...")
        app.logger.info("🔄 Завантаження всіх контактів з HubSpot для експорту...")
        
        # Отримуємо всі контакти з HubSpot (посторінково)
        after = None
        page = 0
        max_pages = 1000  # Збільшено для завантаження всіх контактів
        
        while page < max_pages:
            try:
                # Властивості, які потрібні для контактів
                properties = [
                    'phone', 'phone_number', 'mobilephone', 'hs_phone_number',
                    'phone_number_1', 'email', 'firstname', 'lastname'
                ]
                
                # Отримуємо сторінку контактів
                if after:
                    contacts_response = hubspot_client.crm.contacts.basic_api.get_page(
                        limit=100,
                        after=after,
                        properties=properties
                    )
                else:
                    contacts_response = hubspot_client.crm.contacts.basic_api.get_page(
                        limit=100,
                        properties=properties
                    )
                
                if not contacts_response.results:
                    break
                
                print(f"📄 Сторінка {page + 1}: отримано {len(contacts_response.results)} контактів")
                
                # Обробляємо кожен контакт
                for contact in contacts_response.results:
                    contact_id = str(contact.id)
                    
                    # Отримуємо всі номери телефонів з контакту
                    phone_numbers = []
                    
                    # Перевіряємо всі можливі поля телефонів
                    for phone_field in ['phone', 'phone_number', 'mobilephone', 'hs_phone_number', 'phone_number_1']:
                        phone_value = contact.properties.get(phone_field)
                        if phone_value:
                            phone_numbers.append(phone_value)
                    
                    # Якщо є номери, додаємо контакт до списку
                    # Але також додаємо контакти БЕЗ номерів, якщо потрібно показати всі
                    if phone_numbers:
                        # Для кожного номера створюємо окремий рядок
                        for phone in phone_numbers:
                            contacts_data.append({
                                'id': contact_id,
                                'phone': phone,
                                'email': contact.properties.get('email', ''),
                                'name': f"{contact.properties.get('firstname', '')} {contact.properties.get('lastname', '')}".strip() or 'Без імені'
                            })
                
                # Перевіряємо, чи є ще сторінки
                if not contacts_response.paging or not contacts_response.paging.next:
                    break
                
                after = contacts_response.paging.next.after
                page += 1
                
                # Додаємо затримку між сторінками для rate limiting
                time.sleep(0.5)
                
            except Exception as page_error:
                print(f"❌ Помилка отримання сторінки {page + 1}: {page_error}")
                app.logger.error(f"❌ Помилка отримання сторінки {page + 1}: {page_error}")
                break
        
        print(f"✅ Завантажено {len(contacts_data)} номерів телефонів для експорту")
        app.logger.info(f"✅ Завантажено {len(contacts_data)} номерів телефонів для експорту")
        
        # Створюємо CSV файл
        output = StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow(['ID', 'Номер телефону', 'Email', 'Ім\'я'])
        
        # Дані
        for contact in contacts_data:
            writer.writerow([
                contact['id'],
                contact['phone'],
                contact['email'],
                contact['name']
            ])
        
        # Створюємо відповідь з CSV файлом
        from datetime import datetime
        filename = f"hubspot_contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"❌ Критична помилка при експорті контактів з HubSpot: {e}")
        app.logger.error(f"❌ Критична помилка при експорті контактів з HubSpot: {e}")
        traceback.print_exc()
        flash(f'Помилка експорту контактів: {str(e)}', 'error')
        return redirect(url_for('admin_hubspot_contacts'))

@app.route('/admin/users')
@login_required
def admin_users():
    """Адмін-панель управління користувачами"""
    if current_user.role != 'admin':
        flash('Доступ заборонено')
        return redirect(url_for('dashboard'))
    
    # Отримуємо всіх користувачів (сортуємо за датою створення, найновіші зверху)
    users = User.query.order_by(User.created_at.desc()).all()
    
    # Додаємо кількість документів для кожного користувача
    users_with_docs = []
    for user in users:
        doc_count = UserDocument.query.filter_by(user_id=user.id).count()
        user.doc_count = doc_count
        users_with_docs.append(user)
    
    return render_template('admin_users.html', users=users_with_docs)

@app.route('/admin/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Активування/деактивування користувача"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Користувач не знайдено'})
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Не можна деактивувати власний акаунт'})
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'активовано' if user.is_active else 'деактивовано'
        return jsonify({'success': True, 'message': f'Користувач {user.username} {status}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Видалення користувача"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Користувач не знайдено'})
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Не можна видалити власний акаунт'})
        
        # Перевіряємо, чи є у користувача ліди
        user_leads = Lead.query.filter_by(agent_id=user_id).count()
        if user_leads > 0:
            return jsonify({'success': False, 'message': f'Не можна видалити користувача з {user_leads} лідами. Спочатку передайте ліди іншому агенту.'})
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Користувач {user.username} видалено'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/users/<int:user_id>/unlock', methods=['POST'])
@login_required
def unlock_user(user_id):
    """Розблоковування користувача"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Користувач не знайдено'})
        
        user.unlock_account()
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Акаунт користувача {user.username} розблоковано'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/users/<int:user_id>/commission', methods=['POST'])
@login_required
def update_user_commission(user_id):
    """Оновлення комісії користувача"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        data = request.get_json()
        commission = data.get('commission')
        
        if commission is None:
            return jsonify({'success': False, 'message': 'Не вказано комісію'})
        
        try:
            commission = float(commission)
            if commission < 0 or commission > 100:
                return jsonify({'success': False, 'message': 'Комісія має бути від 0% до 100%'})
        except ValueError:
            return jsonify({'success': False, 'message': 'Невірний формат комісії'})
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Користувач не знайдено'})
        
        user.commission = commission
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Комісію для {user.username} встановлено на {commission}%',
            'commission': commission
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка при оновленні комісії: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

# ===== ДОКУМЕНТИ КОРИСТУВАЧІВ =====
@app.route('/admin/users/<int:user_id>/documents', methods=['GET'])
@login_required
def get_user_documents(user_id):
    """Отримання списку документів користувача"""
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Користувач не знайдено'})
        
        documents = UserDocument.query.filter_by(user_id=user_id).order_by(UserDocument.uploaded_at.desc()).all()
        
        docs_list = []
        for doc in documents:
            docs_list.append({
                'id': doc.id,
                'filename': doc.filename,
                'file_size': doc.file_size,
                'file_type': doc.file_type,
                'uploaded_at': doc.uploaded_at.strftime('%d.%m.%Y %H:%M') if doc.uploaded_at else '',
                'description': doc.description,
                'uploader_name': doc.uploader.username if doc.uploader else 'Невідомо'
            })
        
        return jsonify({'success': True, 'documents': docs_list, 'username': user.username})
        
    except Exception as e:
        app.logger.error(f"Помилка при отриманні документів: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/users/<int:user_id>/documents', methods=['POST'])
@login_required
def upload_user_document(user_id):
    """Завантаження документу користувача в S3"""
    app.logger.info(f"📥 === ПОЧАТОК ЗАВАНТАЖЕННЯ ДОКУМЕНТУ ===")
    app.logger.info(f"   User ID: {user_id}")
    app.logger.info(f"   Current User: {current_user.username} (role: {current_user.role})")
    
    if current_user.role != 'admin':
        app.logger.warning(f"❌ Доступ заборонено для {current_user.username}")
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        user = User.query.get(user_id)
        if not user:
            app.logger.error(f"❌ Користувач з ID {user_id} не знайдено")
            return jsonify({'success': False, 'message': 'Користувач не знайдено'})
        
        app.logger.info(f"✅ Користувач знайдено: {user.username}")
        
        if 'file' not in request.files:
            app.logger.error("❌ Файл не знайдено в request.files")
            app.logger.error(f"   Доступні ключі: {list(request.files.keys())}")
            return jsonify({'success': False, 'message': 'Файл не знайдено'})
        
        file = request.files['file']
        app.logger.info(f"✅ Файл отримано з request")
        
        if file.filename == '':
            app.logger.error("❌ Ім'я файлу порожнє")
            return jsonify({'success': False, 'message': 'Файл не вибрано'})
        
        # Генеруємо унікальне ім'я файлу
        import uuid
        from werkzeug.utils import secure_filename
        
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"user_documents/{user_id}/{uuid.uuid4().hex}{file_extension}"
        
        app.logger.info(f"📄 Інформація про файл:")
        app.logger.info(f"   Оригінальна назва: {original_filename}")
        app.logger.info(f"   Розширення: {file_extension}")
        app.logger.info(f"   Унікальна назва: {unique_filename}")
        app.logger.info(f"   Content-Type: {file.content_type}")
        
        # Отримуємо розмір файлу
        file.seek(0, 2)  # Переміщуємось в кінець файлу
        file_size = file.tell()
        file.seek(0)  # Повертаємось на початок
        
        app.logger.info(f"   Розмір файлу: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
        
        if file_size > 10 * 1024 * 1024:
            app.logger.error(f"❌ Файл занадто великий: {file_size/1024/1024:.2f} MB")
            return jsonify({'success': False, 'message': 'Файл занадто великий (макс. 10MB)'})
        
        # Завантажуємо файл в S3
        app.logger.info("🚀 Початок завантаження в S3...")
        s3_url = upload_file_to_s3(file, unique_filename)
        app.logger.info(f"✅ Файл завантажено в S3: {s3_url}")
        
        # Створюємо запис в БД
        app.logger.info("💾 Створення запису в БД...")
        document = UserDocument(
            user_id=user_id,
            filename=original_filename,
            file_path=unique_filename,  # Зберігаємо шлях в S3
            file_size=file_size,
            file_type=file.content_type,
            uploaded_by=current_user.id,
            description=request.form.get('description', '')
        )
        
        db.session.add(document)
        db.session.commit()
        
        app.logger.info(f"✅ Запис створено в БД (ID: {document.id})")
        app.logger.info(f"🎉 === ЗАВАНТАЖЕННЯ ЗАВЕРШЕНО УСПІШНО ===")
        
        return jsonify({
            'success': True,
            'message': f'Документ "{original_filename}" успішно завантажено в S3',
            'document': {
                'id': document.id,
                'filename': document.filename,
                'file_size': document.file_size,
                'uploaded_at': document.uploaded_at.strftime('%d.%m.%Y %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"❌❌❌ КРИТИЧНА ПОМИЛКА ❌❌❌")
        app.logger.error(f"   Тип помилки: {type(e).__name__}")
        app.logger.error(f"   Повідомлення: {str(e)}")
        app.logger.error(f"   Traceback:\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/admin/users/<int:user_id>/documents/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_user_document(user_id, doc_id):
    """Видалення документу користувача з S3"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    try:
        document = UserDocument.query.filter_by(id=doc_id, user_id=user_id).first()
        if not document:
            return jsonify({'success': False, 'message': 'Документ не знайдено'})
        
        # Видаляємо файл з S3
        delete_file_from_s3(document.file_path)
        
        filename = document.filename
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Документ "{filename}" видалено з S3'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка при видаленні документу: {e}")
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

# ===== ВАЛІДАЦІЯ ТЕЛЕФОННИХ НОМЕРІВ =====
@app.route('/api/check-phone', methods=['POST'])
@login_required
def check_phone_number():
    """Real-time перевірка номера телефону на дублікати"""
    try:
        data = request.get_json()
        phone_input = data.get('phone', '').strip()
        
        # Логування для діагностики
        app.logger.info(f"🔍 Перевірка номера: '{phone_input}'")
        
        # Мінімальна перевірка - має бути хоча б "+" і цифри
        if not phone_input or len(phone_input) < 2:
            return jsonify({
                'success': False,
                'count': 0,
                'matches': [],
                'message': 'Введіть номер телефону'
            })
        
        # Очищаємо номер від спец символів для пошуку
        clean_phone = ''.join(filter(str.isdigit, phone_input))
        
        # Перевіряємо, чи є мінімум 4 цифри для пошуку
        if len(clean_phone) < 4:
            return jsonify({
                'success': False,
                'count': 0,
                'matches': [],
                'message': 'Введіть мінімум 4 цифри'
            })
        
        app.logger.info(f"   Очищений номер: '{clean_phone}'")
        
        # Шукаємо ліди з схожими номерами (перевіряємо phone та second_phone)
        # Різна логіка для PostgreSQL та SQLite
        database_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        if database_uri.startswith('postgresql'):
            # PostgreSQL підтримує regexp_replace - перевіряємо обидва поля телефонів
            matching_leads = Lead.query.filter(
                (func.regexp_replace(Lead.phone, '[^0-9]', '', 'g').like(f'%{clean_phone}%')) |
                (func.regexp_replace(Lead.second_phone, '[^0-9]', '', 'g').like(f'%{clean_phone}%'))
            ).limit(10).all()
        else:
            # Для SQLite використовуємо простий LIKE (номери вже відформатовані)
            # Шукаємо по частковому співпадінню в обох полях
            matching_leads = Lead.query.filter(
                (Lead.phone.like(f'%{clean_phone}%')) |
                (Lead.second_phone.like(f'%{clean_phone}%'))
            ).limit(20).all()  # Більше ліміт, бо потім фільтруємо
            
            # Додаткова фільтрація в Python для SQLite
            filtered_leads = []
            for lead in matching_leads:
                lead_phone_clean = ''.join(filter(str.isdigit, lead.phone or ''))
                lead_second_phone_clean = ''.join(filter(str.isdigit, lead.second_phone or ''))
                if clean_phone in lead_phone_clean or clean_phone in lead_second_phone_clean:
                    filtered_leads.append(lead)
            matching_leads = filtered_leads[:10]
        
        app.logger.info(f"   Знайдено збігів: {len(matching_leads)}")
        
        # Додаткове логування для діагностики
        if matching_leads:
            for lead in matching_leads[:3]:  # Перші 3 для перевірки
                app.logger.info(f"      Знайдено: {lead.deal_name} - {lead.phone}")
        
        # Формуємо результат
        matches = []
        for lead in matching_leads:
            matches.append({
                'id': lead.id,
                'name': lead.deal_name,
                'phone': lead.phone,
                'email': lead.email,
                'status': lead.status,
                'agent': lead.agent.username if lead.agent else 'Не призначено',
                'created_at': lead.created_at.strftime('%d.%m.%Y') if lead.created_at else ''
            })
        
        return jsonify({
            'success': True,
            'count': len(matching_leads),
            'matches': matches,
            'search_term': phone_input
        })
        
    except Exception as e:
        app.logger.error(f"❌ Помилка при перевірці номера: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'count': 0,
            'matches': [],
            'message': f'Помилка: {str(e)}'
        })

@app.route('/admin/test-s3')
@login_required
def test_s3_connection():
    """Тестування підключення до S3"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    app.logger.info("🧪 === ТЕСТ S3 ПІДКЛЮЧЕННЯ ===")
    
    try:
        s3_client = get_s3_client()
        if not s3_client:
            return jsonify({
                'success': False,
                'message': 'S3 клієнт не створено - перевірте змінні середовища',
                'config': {
                    'AWS_ACCESS_KEY_ID': '✅' if app.config.get('AWS_ACCESS_KEY_ID') else '❌',
                    'AWS_SECRET_ACCESS_KEY': '✅' if app.config.get('AWS_SECRET_ACCESS_KEY') else '❌',
                    'AWS_S3_BUCKET': app.config.get('AWS_S3_BUCKET', '❌ не встановлено'),
                    'AWS_REGION': app.config.get('AWS_REGION', 'за замовчуванням')
                }
            })
        
        # Тестуємо список об'єктів
        bucket = app.config['AWS_S3_BUCKET']
        app.logger.info(f"   Перевіряємо bucket: {bucket}")
        
        response = s3_client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        app.logger.info(f"✅ Успішно підключено до S3!")
        
        return jsonify({
            'success': True,
            'message': 'S3 налаштовано правильно!',
            'config': {
                'AWS_S3_BUCKET': bucket,
                'AWS_REGION': app.config['AWS_REGION'],
                'objects_count': response.get('KeyCount', 0)
            }
        })
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        app.logger.error(f"❌ S3 ClientError: {error_code} - {error_message}")
        
        return jsonify({
            'success': False,
            'message': f'Помилка S3: {error_code}',
            'details': error_message
        })
    except Exception as e:
        app.logger.error(f"❌ Загальна помилка: {type(e).__name__}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Помилка: {str(e)}'
        })

@app.route('/documents/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    """Завантаження документу з S3"""
    try:
        document = UserDocument.query.get(doc_id)
        if not document:
            flash('Документ не знайдено', 'error')
            return redirect(url_for('profile'))
        
        # Перевірка доступу: адмін або власник документу
        if current_user.role != 'admin' and current_user.id != document.user_id:
            flash('Доступ заборонено', 'error')
            return redirect(url_for('profile'))
        
        # Завантажуємо файл з S3
        file_obj = download_file_from_s3(document.file_path)
        
        from flask import send_file
        return send_file(
            file_obj,
            as_attachment=True,
            download_name=document.filename,
            mimetype=document.file_type or 'application/octet-stream'
        )
        
    except Exception as e:
        app.logger.error(f"Помилка при завантаженні документу: {e}")
        flash('Помилка при завантаженні документу з S3', 'error')
        return redirect(url_for('profile'))

# ===== ERROR HANDLERS =====
@app.errorhandler(Exception)
def handle_exception(error):
    """Глобальний обробник помилок"""
    db.session.rollback()
    app.logger.error(f"Unhandled exception: {error}", exc_info=True)
    
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    return render_template('error.html', error="Виникла помилка. Спробуйте пізніше."), 500

@app.errorhandler(404)
def not_found(error):
    """Обробник 404 помилки"""
    app.logger.warning(f"404 error: {request.url}")
    
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Not found'}), 404
    
    return render_template('error.html', error="Сторінку не знайдено"), 404

@app.errorhandler(500)
def internal_error(error):
    """Обробник 500 помилки"""
    db.session.rollback()
    app.logger.error(f"500 error: {error}")
    
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    return render_template('error.html', error="Внутрішня помилка сервера"), 500

@app.route('/admin/hubspot-stages', methods=['GET'])
@login_required
def get_hubspot_stages():
    """Отримати всі стадії (stages) з HubSpot pipeline для налаштування маппінгу"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ тільки для адміністратора'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        # Отримуємо інформацію про pipeline "Лиды" (ID: 2341107958)
        pipeline = hubspot_client.crm.pipelines.pipelines_api.get_by_id(
            object_type='deals',
            pipeline_id='2341107958'
        )
        
        stages_info = []
        for stage in pipeline.stages:
            stages_info.append({
                'id': stage.id,
                'label': stage.label,
                'display_order': stage.display_order
            })
        
        # Також отримуємо, які dealstage є в поточних лідах
        leads_with_hubspot = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).limit(20).all()
        current_stages = {}
        
        for lead in leads_with_hubspot:
            if lead.hubspot_deal_id:
                try:
                    deal = hubspot_client.crm.deals.basic_api.get_by_id(
                        deal_id=lead.hubspot_deal_id,
                        properties=["dealstage"]
                    )
                    stage_id = deal.properties.get('dealstage')
                    if stage_id:
                        if stage_id not in current_stages:
                            current_stages[stage_id] = {
                                'count': 0,
                                'leads_sample': []
                            }
                        current_stages[stage_id]['count'] += 1
                        if len(current_stages[stage_id]['leads_sample']) < 3:
                            current_stages[stage_id]['leads_sample'].append({
                                'id': lead.id,
                                'name': lead.deal_name,
                                'current_status': lead.status
                            })
                except Exception as e:
                    print(f"Помилка отримання deal {lead.hubspot_deal_id}: {e}")
        
        return jsonify({
            'success': True,
            'pipeline_stages': stages_info,
            'current_stages_usage': current_stages,
            'current_mapping': {
                '3204738258': 'new (Новая заявка)',
                '3204738259': 'contacted (Контакт встановлено)',
                '3204738261': 'qualified (Назначена встреча)',
                '3204738262': 'qualified (Встреча проведена)',
                '3204738265': 'qualified (Переговоры)',
                '3204738266': 'qualified (Задаток)',
                '3204738267': 'closed (Сделка закрыта)'
            }
        })
        
    except Exception as e:
        app.logger.error(f"Помилка отримання stages з HubSpot: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/api/hubspot/pipelines', methods=['GET'])
@login_required
def get_all_hubspot_pipelines():
    """Отримати всі pipelines з HubSpot API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ тільки для адміністратора'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        # Отримуємо всі pipelines для deals
        pipelines = hubspot_client.crm.pipelines.pipelines_api.get_all(object_type='deals')
        
        pipelines_list = []
        for pipeline in pipelines.results:
            stages_list = []
            if pipeline.stages:
                for stage in pipeline.stages:
                    stages_list.append({
                        'id': stage.id,
                        'label': stage.label,
                        'display_order': stage.display_order
                    })
            
            pipelines_list.append({
                'id': pipeline.id,
                'label': pipeline.label,
                'display_order': pipeline.display_order,
                'archived': getattr(pipeline, 'archived', False),
                'created_at': getattr(pipeline, 'created_at', None),
                'updated_at': getattr(pipeline, 'updated_at', None),
                'stages': stages_list,
                'stages_count': len(stages_list)
            })
        
        # Сортуємо за display_order
        pipelines_list.sort(key=lambda x: x.get('display_order', 999))
        
        return jsonify({
            'success': True,
            'pipelines': pipelines_list,
            'total_count': len(pipelines_list)
        })
        
    except Exception as e:
        app.logger.error(f"Помилка отримання pipelines з HubSpot: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})


# ==================== PROPERTY ROUTES ====================

@app.route('/properties')
@login_required
def properties():
    """Список всіх нерухомості"""
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('properties.html', properties=properties)


@app.route('/properties/<int:property_id>')
@login_required
def property_detail(property_id):
    """Детальна інформація про нерухомість"""
    property_obj = Property.query.get_or_404(property_id)
    return render_template('property_detail.html', property=property_obj)


@app.route('/properties/create', methods=['GET', 'POST'])
@login_required
def create_property():
    """Створення нової нерухомості (тільки для адмінів)"""
    if current_user.role != 'admin':
        flash('Доступ заборонено. Тільки адміністратори можуть створювати нерухомість.', 'error')
        return redirect(url_for('properties'))
    
    form = PropertyForm()
    if form.validate_on_submit():
        try:
            property_obj = Property(
                name=form.name.data,
                location_country=form.location_country.data,
                location_city=form.location_city.data,
                location_district=form.location_district.data,
                price_from=form.price_from.data,
                price_to=form.price_to.data if form.price_to.data else None,
                description=form.description.data,
                payment_type=form.payment_type.data,
                created_by=current_user.id
            )
            
            db.session.add(property_obj)
            db.session.flush()  # Отримуємо ID нерухомості
            
            # Обробка фотографій
            photos = request.files.getlist('photos')
            app.logger.info(f"📸 Завантаження фото: {len(photos)} файлів")
            for photo in photos:
                if photo and photo.filename:
                    # Генеруємо унікальне ім'я файлу
                    ext = photo.filename.rsplit('.', 1)[1].lower() if '.' in photo.filename else 'jpg'
                    timestamp = int(time.time())
                    filename = f"{property_obj.id}_{timestamp}_{photo.filename}"
                    
                    # Завантажуємо файл
                    file_url = upload_file_to_s3(photo, filename)
                    if file_url:
                        property_photo = PropertyPhoto(
                            property_id=property_obj.id,
                            filename=filename,
                            file_path=file_url
                        )
                        db.session.add(property_photo)
                        app.logger.info(f"✅ Фото додано: {filename}")
            
            # Обробка документів
            documents = request.files.getlist('documents')
            app.logger.info(f"📄 Завантаження документів: {len(documents)} файлів")
            for document in documents:
                if document and document.filename:
                    # Генеруємо унікальне ім'я файлу
                    ext = document.filename.rsplit('.', 1)[1].lower() if '.' in document.filename else 'pdf'
                    timestamp = int(time.time())
                    filename = f"{property_obj.id}_{timestamp}_{document.filename}"
                    
                    # Завантажуємо файл
                    file_url = upload_file_to_s3(document, filename)
                    if file_url:
                        property_doc = PropertyDocument(
                            property_id=property_obj.id,
                            filename=document.filename,
                            file_path=file_url
                        )
                        db.session.add(property_doc)
                        app.logger.info(f"✅ Документ додано: {filename}")
            
            db.session.commit()
            
            flash('Нерухомість успішно створена!', 'success')
            return redirect(url_for('property_detail', property_id=property_obj.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Помилка створення нерухомості: {e}")
            import traceback
            app.logger.error(traceback.format_exc())
            flash('Помилка при створенні нерухомості.', 'error')
    
    return render_template('create_property.html', form=form)


@app.route('/properties/<int:property_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_property(property_id):
    """Редагування нерухомості (тільки для адмінів)"""
    if current_user.role != 'admin':
        flash('Доступ заборонено. Тільки адміністратори можуть редагувати нерухомість.', 'error')
        return redirect(url_for('properties'))
    
    property_obj = Property.query.get_or_404(property_id)
    form = PropertyForm(obj=property_obj)
    
    if form.validate_on_submit():
        try:
            property_obj.name = form.name.data
            property_obj.location_country = form.location_country.data
            property_obj.description = form.description.data
            property_obj.location_city = form.location_city.data
            property_obj.location_district = form.location_district.data
            property_obj.price_from = form.price_from.data
            property_obj.price_to = form.price_to.data if form.price_to.data else None
            property_obj.payment_type = form.payment_type.data
            
            # Обробка НОВИХ фотографій
            photos = request.files.getlist('photos')
            app.logger.info(f"📸 Додавання нових фото: {len(photos)} файлів")
            for photo in photos:
                if photo and photo.filename:
                    ext = photo.filename.rsplit('.', 1)[1].lower() if '.' in photo.filename else 'jpg'
                    timestamp = int(time.time())
                    filename = f"{property_obj.id}_{timestamp}_{photo.filename}"
                    
                    file_url = upload_file_to_s3(photo, filename)
                    if file_url:
                        property_photo = PropertyPhoto(
                            property_id=property_obj.id,
                            filename=filename,
                            file_path=file_url
                        )
                        db.session.add(property_photo)
                        app.logger.info(f"✅ Нове фото додано: {filename}")
            
            # Обробка НОВИХ документів
            documents = request.files.getlist('documents')
            app.logger.info(f"📄 Додавання нових документів: {len(documents)} файлів")
            for document in documents:
                if document and document.filename:
                    ext = document.filename.rsplit('.', 1)[1].lower() if '.' in document.filename else 'pdf'
                    timestamp = int(time.time())
                    filename = f"{property_obj.id}_{timestamp}_{document.filename}"
                    
                    file_url = upload_file_to_s3(document, filename)
                    if file_url:
                        property_doc = PropertyDocument(
                            property_id=property_obj.id,
                            filename=document.filename,
                            file_path=file_url
                        )
                        db.session.add(property_doc)
                        app.logger.info(f"✅ Новий документ додано: {filename}")
            
            db.session.commit()
            
            flash('Нерухомість успішно оновлена!', 'success')
            return redirect(url_for('property_detail', property_id=property_obj.id))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Помилка оновлення нерухомості: {e}")
            import traceback
            app.logger.error(traceback.format_exc())
            flash('Помилка при оновленні нерухомості.', 'error')
    
    return render_template('edit_property.html', form=form, property=property_obj)


@app.route('/properties/<int:property_id>/delete', methods=['POST'])
@login_required
def delete_property(property_id):
    """Видалення нерухомості (тільки для адмінів)"""
    if current_user.role != 'admin':
        flash('Доступ заборонено. Тільки адміністратори можуть видаляти нерухомість.', 'error')
        return redirect(url_for('properties'))
    
    property_obj = Property.query.get_or_404(property_id)
    
    try:
        # Видаляємо всі пов'язані файли з S3
        for photo in property_obj.photos:
            delete_file_from_s3(photo.filename)
        
        for unit in property_obj.units:
            for unit_photo in unit.photos:
                delete_file_from_s3(unit_photo.filename)
        
        for document in property_obj.documents:
            delete_file_from_s3(document.filename)
        
        db.session.delete(property_obj)
        db.session.commit()
        
        flash('Нерухомість успішно видалена!', 'success')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка видалення нерухомості: {e}")
        flash('Помилка при видаленні нерухомості.', 'error')
    
    return redirect(url_for('properties'))


@app.route('/properties/<int:property_id>/units/add', methods=['POST'])
@login_required
def add_property_unit(property_id):
    """Додавання планування до нерухомості (тільки для адмінів)"""
    app.logger.info(f"📋 === ДОДАВАННЯ ПЛАНУВАННЯ ===")
    app.logger.info(f"   Property ID: {property_id}")
    app.logger.info(f"   User: {current_user.username} (role: {current_user.role})")
    
    if current_user.role != 'admin':
        app.logger.warning("⚠️ Доступ заборонено - користувач не адмін")
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    property_obj = Property.query.get_or_404(property_id)
    
    try:
        # Отримуємо дані з JSON
        data = request.get_json()
        app.logger.info(f"   Отримані дані: {data}")
        
        # Валідуємо дані
        if not data or 'unit_type' not in data or 'size_from' not in data or 'price_per_unit' not in data:
            app.logger.error("❌ Відсутні обов'язкові поля")
            return jsonify({'success': False, 'message': 'Невалідні дані - відсутні обов\'язкові поля'})
        
        # Створюємо планування
        unit = PropertyUnit(
            property_id=property_id,
            unit_type=data['unit_type'],
            size_from=float(data['size_from']),
            size_to=float(data['size_to']) if data.get('size_to') else None,
            price_per_unit=float(data['price_per_unit'])
        )
        
        db.session.add(unit)
        db.session.commit()
        
        app.logger.info(f"✅ Планування додано успішно: ID={unit.id}")
        return jsonify({'success': True, 'message': 'Планування додано успішно!'})
        
    except ValueError as e:
        db.session.rollback()
        app.logger.error(f"❌ Помилка валідації даних: {e}")
        return jsonify({'success': False, 'message': 'Невалідні дані - перевірте числові значення'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"❌ Помилка додавання планування: {type(e).__name__}: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Помилка при додаванні планування: {str(e)}'})


@app.route('/properties/<int:property_id>/units/<int:unit_id>/delete', methods=['POST'])
@login_required
def delete_property_unit(property_id, unit_id):
    """Видалення планування (тільки для адмінів)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    unit = PropertyUnit.query.get_or_404(unit_id)
    
    try:
        # Видаляємо фото планування з S3
        for photo in unit.photos:
            delete_file_from_s3(photo.filename)
        
        db.session.delete(unit)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Планування видалено успішно!'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка видалення планування: {e}")
        return jsonify({'success': False, 'message': 'Помилка при видаленні планування'})


@app.route('/properties/<int:property_id>/upload-photos', methods=['POST'])
@login_required
def upload_property_photos(property_id):
    """Завантаження фото нерухомості в S3 (тільки для адмінів)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    property_obj = Property.query.get_or_404(property_id)
    
    if 'photos' not in request.files:
        return jsonify({'success': False, 'message': 'Файли не вибрані'})
    
    files = request.files.getlist('photos')
    uploaded_files = []
    
    try:
        for file in files:
            if file and file.filename:
                # Перевіряємо тип файлу
                if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    continue
                
                # Генеруємо унікальне ім'я файлу для S3
                unique_filename = f"properties/{property_id}_{int(time.time())}_{file.filename}"
                
                # Завантажуємо файл в S3
                s3_url = upload_file_to_s3(file, unique_filename)
                
                # Додаємо запис в базу даних
                photo = PropertyPhoto(
                    property_id=property_id,
                    filename=unique_filename,  # Зберігаємо шлях в S3 або локально
                    file_path=s3_url,  # URL файлу в S3 або локально
                    file_size=len(file.read()),
                    file_type=file.content_type
                )
                file.seek(0)  # Повертаємо позицію файлу на початок
                db.session.add(photo)
                uploaded_files.append(unique_filename)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Завантажено {len(uploaded_files)} фото'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка завантаження фото в S3: {e}")
        return jsonify({'success': False, 'message': 'Помилка при завантаженні фото'})


@app.route('/properties/<int:property_id>/upload-documents', methods=['POST'])
@login_required
def upload_property_documents(property_id):
    """Завантаження документів нерухомості в S3 (тільки для адмінів, максимум 5)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    property_obj = Property.query.get_or_404(property_id)
    
    # Перевіряємо кількість документів
    if len(property_obj.documents) >= 5:
        return jsonify({'success': False, 'message': 'Максимум 5 документів на проект'})
    
    if 'documents' not in request.files:
        return jsonify({'success': False, 'message': 'Файли не вибрані'})
    
    files = request.files.getlist('documents')
    uploaded_files = []
    
    try:
        for file in files:
            if file and file.filename and len(property_obj.documents) + len(uploaded_files) < 5:
                # Перевіряємо тип файлу
                if not file.filename.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
                    continue
                
                # Генеруємо унікальне ім'я файлу для S3
                unique_filename = f"documents/{property_id}_{int(time.time())}_{file.filename}"
                
                # Завантажуємо файл в S3
                s3_url = upload_file_to_s3(file, unique_filename)
                
                # Додаємо запис в базу даних
                document = PropertyDocument(
                    property_id=property_id,
                    filename=unique_filename,  # Зберігаємо шлях в S3
                    file_path=s3_url,  # URL файлу в S3
                    file_size=len(file.read()),
                    file_type=file.content_type,
                    description=request.form.get('description', '')
                )
                file.seek(0)  # Повертаємо позицію файлу на початок
                db.session.add(document)
                uploaded_files.append(unique_filename)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Завантажено {len(uploaded_files)} документів'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка завантаження документів в S3: {e}")
        return jsonify({'success': False, 'message': 'Помилка при завантаженні документів'})


@app.route('/units/<int:unit_id>/upload-photos', methods=['POST'])
@login_required
def upload_unit_photos(unit_id):
    """Завантаження фото планування в S3 (тільки для адмінів)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ заборонено'})
    
    unit = PropertyUnit.query.get_or_404(unit_id)
    
    if 'photos' not in request.files:
        return jsonify({'success': False, 'message': 'Файли не вибрані'})
    
    files = request.files.getlist('photos')
    uploaded_files = []
    
    try:
        for file in files:
            if file and file.filename:
                # Перевіряємо тип файлу
                if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    continue
                
                # Генеруємо унікальне ім'я файлу для S3
                unique_filename = f"units/{unit_id}_{int(time.time())}_{file.filename}"
                
                # Завантажуємо файл в S3
                s3_url = upload_file_to_s3(file, unique_filename)
                
                # Додаємо запис в базу даних
                photo = UnitPhoto(
                    unit_id=unit_id,
                    filename=unique_filename,  # Зберігаємо шлях в S3
                    file_path=s3_url,  # URL файлу в S3
                    file_size=len(file.read()),
                    file_type=file.content_type
                )
                file.seek(0)  # Повертаємо позицію файлу на початок
                db.session.add(photo)
                uploaded_files.append(unique_filename)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Завантажено {len(uploaded_files)} фото планування'})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Помилка завантаження фото планування в S3: {e}")
        return jsonify({'success': False, 'message': 'Помилка при завантаженні фото планування'})


# Запускаємо фонову синхронізацію з HubSpot автоматично при завантаженні модуля
# Це працює і для локального запуску, і для production (Gunicorn)
try:
    start_background_sync()
    print("✅ Фонова синхронізація HubSpot запущена автоматично")
except Exception as e:
    print(f"⚠️ Не вдалося запустити фонову синхронізацію: {e}")
    app.logger.warning(f"⚠️ Не вдалося запустити фонову синхронізацію: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Створюємо адміна якщо його немає
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            from werkzeug.security import generate_password_hash
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Створено адміна: username='admin', password='admin123'")

# ===== ДІАГНОСТИЧНИЙ ЕНДПОІНТ =====
@app.route('/api/diagnostic', methods=['GET'])
@login_required
def diagnostic():
    """Діагностичний ендпоінт для перевірки конфігурації на продакшені"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ тільки для адміністраторів'})
    
    diagnostic_info = {
        'success': True,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'environment': {
            'database': {
                'type': 'PostgreSQL' if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql') else 'SQLite',
                'configured': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
                'connection_test': None
            },
            'hubspot': {
                'api_key_set': bool(HUBSPOT_API_KEY),
                'client_configured': hubspot_client is not None,
                'connection_test': None
            },
            's3': {
                'access_key_set': bool(app.config.get('AWS_ACCESS_KEY_ID')),
                'secret_key_set': bool(app.config.get('AWS_SECRET_ACCESS_KEY')),
                'bucket_set': bool(app.config.get('AWS_S3_BUCKET')),
                'region': app.config.get('AWS_REGION', 'not set'),
                'client_configured': get_s3_client() is not None
            },
            'flask': {
                'secret_key_set': bool(app.config.get('SECRET_KEY')),
                'csrf_enabled': csrf._exempt_views == set() if hasattr(csrf, '_exempt_views') else True
            }
        }
    }
    
    # Тест підключення до БД
    try:
        db.session.execute(db.text('SELECT 1'))
        diagnostic_info['environment']['database']['connection_test'] = 'success'
    except Exception as e:
        diagnostic_info['environment']['database']['connection_test'] = f'error: {str(e)}'
    
    # Тест HubSpot підключення
    if hubspot_client:
        try:
            hubspot_client.crm.contacts.basic_api.get_page(limit=1)
            diagnostic_info['environment']['hubspot']['connection_test'] = 'success'
        except Exception as e:
            error_str = str(e)
            diagnostic_info['environment']['hubspot']['connection_test'] = f'error: {error_str[:200]}'
            # Додаємо інформацію про тип помилки
            if '401' in error_str or 'Unauthorized' in error_str:
                diagnostic_info['environment']['hubspot']['connection_test'] += ' (недійсний API ключ)'
            elif '403' in error_str or 'Forbidden' in error_str:
                diagnostic_info['environment']['hubspot']['connection_test'] += ' (немає прав доступу)'
            elif '429' in error_str:
                diagnostic_info['environment']['hubspot']['connection_test'] += ' (перевищено ліміт запитів)'
    else:
        diagnostic_info['environment']['hubspot']['connection_test'] = 'client_not_configured'
        if not HUBSPOT_API_KEY:
            diagnostic_info['environment']['hubspot']['connection_test'] += ' (HUBSPOT_API_KEY не встановлено)'
        else:
            diagnostic_info['environment']['hubspot']['connection_test'] += ' (помилка ініціалізації клієнта)'
    
    return jsonify(diagnostic_info)
