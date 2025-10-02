from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from wtforms import Form, StringField, PasswordField, TextAreaField, SelectField, HiddenField, validators
from dotenv import load_dotenv
import os
import time
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from hubspot import HubSpot
from logging_config import setup_logging
from hubspot_rate_limiter import hubspot_rate_limiter

# Завантажуємо змінні середовища
load_dotenv()

app = Flask(__name__)

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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://localhost/real_estate_agents'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
# Тимчасово вимкнуто для сумісності зі старими формами
# csrf = CSRFProtect(app)
# TODO: Додати CSRF токени у всі форми перед активацією

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
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

# Форми
class LoginForm(Form):
    username = StringField('Ім\'я користувача', [validators.Length(min=4, max=25)])
    password = PasswordField('Пароль', [validators.DataRequired()])

class LeadForm(Form):
    deal_name = StringField('Deal name', [validators.DataRequired(), validators.Length(min=2, max=100)])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    phone = StringField('Phone number', [validators.DataRequired(), validators.Length(max=20)])
    budget = SelectField('Budget', choices=[
        ('до 200к', 'до 200к'),
        ('200к–500к', '200к–500к'),
        ('500к–1млн', '500к–1млн'),
        ('1млн+', '1млн+')
    ], validators=[validators.DataRequired()])
    notes = TextAreaField('Примітки', [validators.Length(max=500)])
    agent_id = HiddenField('Agent ID')

class NoteForm(Form):
    note_text = TextAreaField('Нотатка', [validators.DataRequired(), validators.Length(min=1, max=1000)])

class RegistrationForm(Form):
    username = StringField('Ім\'я користувача', [validators.DataRequired(), validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Пароль', [validators.DataRequired(), validators.Length(min=6)])
    confirm_password = PasswordField('Підтвердіть пароль', [validators.DataRequired()])
    
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

class NoteStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    note_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='sent')  # sent, read, replied
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

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

class LeadEditForm(Form):
    deal_name = StringField('Deal name', [validators.DataRequired(), validators.Length(min=2, max=100)])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    phone = StringField('Phone number', [validators.DataRequired(), validators.Length(max=20)])
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

def fetch_notes_from_hubspot(lead):
    """Отримує нотатки з HubSpot для контакту та угоди"""
    if not hubspot_client or not lead.hubspot_contact_id:
        print(f"Немає HubSpot клієнта або ID контакту для ліда {lead.id}")
        return []
    
    notes = []
    
    try:
        # Використовуємо search API для пошуку нотаток
        from hubspot.crm.objects.notes import PublicObjectSearchRequest
        from hubspot.crm.objects.notes import Filter, FilterGroup
        
        # Створюємо запит для пошуку нотаток
        search_request = PublicObjectSearchRequest(
            filter_groups=[
                FilterGroup(
                    filters=[
                        Filter(
                            property_name="hs_note_body",
                            operator="HAS_PROPERTY"
                        )
                    ]
                )
            ],
            properties=["hs_note_body", "hs_timestamp", "hs_createdate"],
            limit=100
        )
        
        # Виконуємо пошук нотаток
        search_results = hubspot_client.crm.objects.notes.search_api.do_search(
            public_object_search_request=search_request
        )
        
        if search_results.results:
            for note in search_results.results:
                if note.properties and note.properties.get('hs_note_body'):
                    notes.append({
                        'id': str(note.id),
                        'body': note.properties.get('hs_note_body', ''),
                        'timestamp': note.properties.get('hs_timestamp'),
                        'createdate': note.properties.get('hs_createdate'),
                        'source': 'search'
                    })
        
        print(f"Отримано {len(notes)} нотаток з HubSpot для ліда {lead.id}")
        return notes
        
    except Exception as e:
        print(f"Помилка отримання нотаток з HubSpot для ліда {lead.id}: {e}")
        return []

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

def sync_notes_from_hubspot(lead):
    """Синхронізує нотатки з HubSpot в локальну БД"""
    if not hubspot_client or not lead.hubspot_contact_id:
        return False
    
    try:
        # Отримуємо нотатки з HubSpot
        hubspot_notes = fetch_notes_from_hubspot(lead)
        
        for note_data in hubspot_notes:
            # Перевіряємо, чи існує вже така нотатка в локальній БД
            existing_note = NoteStatus.query.filter_by(
                lead_id=lead.id,
                note_text=note_data['body']
            ).first()
            
            if not existing_note and note_data['body'].strip():
                # Створюємо нову нотатку в локальній БД
                new_note = NoteStatus(
                    lead_id=lead.id,
                    note_text=note_data['body'],
                    status='read'  # Нотатки з HubSpot вважаємо прочитаними
                )
                
                # Встановлюємо дату створення з HubSpot, якщо є
                if note_data.get('createdate'):
                    try:
                        from datetime import datetime
                        # HubSpot дата в форматі timestamp (мілісекунди)
                        timestamp = int(note_data['createdate']) / 1000
                        new_note.created_at = datetime.fromtimestamp(timestamp)
                    except (ValueError, TypeError):
                        pass  # Використовуємо поточну дату
                
                db.session.add(new_note)
                print(f"Додано нотатку з HubSpot для ліда {lead.id}: {note_data['body'][:50]}...")
        
        db.session.commit()
        print(f"Синхронізовано {len(hubspot_notes)} нотаток з HubSpot для ліда {lead.id}")
        return True
        
    except Exception as e:
        print(f"Помилка синхронізації нотаток для ліда {lead.id}: {e}")
        db.session.rollback()
        return False

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
                        from datetime import datetime
                        # HubSpot дата в форматі timestamp (мілісекунди)
                        timestamp = int(activity_data['createdate']) / 1000
                        new_activity.created_at = datetime.fromtimestamp(timestamp)
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

def create_note_in_hubspot(lead, note_text, note_type="note"):
    """Створює нотатку в HubSpot для контакту або угоди"""
    if not hubspot_client or not lead.hubspot_contact_id:
        print(f"Немає HubSpot клієнта або ID контакту для ліда {lead.id}")
        return False
    
    try:
        # Створюємо нотатку в HubSpot
        note_properties = {
            "hs_note_body": note_text,
            "hs_timestamp": int(time.time() * 1000)  # timestamp в мілісекундах
        }
        
        from hubspot.crm.objects.notes import SimplePublicObjectInput as NoteInput
        note_input = NoteInput(properties=note_properties)
        
        # Створюємо нотатку
        hubspot_note = hubspot_client.crm.objects.notes.basic_api.create(simple_public_object_input=note_input)
        hubspot_note_id = str(hubspot_note.id)
        print(f"Створено нотатку в HubSpot: {hubspot_note_id}")
        
        # Прив'язуємо нотатку до контакту
        try:
            from hubspot.crm.associations import BatchInputPublicAssociation
            from hubspot.crm.associations import PublicAssociation
            
            # Створюємо асоціацію з контактом
            association = PublicAssociation(
                _from=hubspot_note_id,
                to=lead.hubspot_contact_id,
                type="note_to_contact"
            )
            
            batch_input = BatchInputPublicAssociation(inputs=[association])
            
            hubspot_client.crm.associations.batch_api.create(
                "notes",
                "contacts",
                batch_input_public_association=batch_input
            )
            print(f"Нотатку {hubspot_note_id} прив'язано до контакту {lead.hubspot_contact_id}")
        except Exception as assoc_error:
            print(f"Помилка прив'язки нотатки до контакту: {assoc_error}")
        
        # Якщо є угода, прив'язуємо нотатку і до неї
        if lead.hubspot_deal_id:
            try:
                from hubspot.crm.associations import BatchInputPublicAssociation
                from hubspot.crm.associations import PublicAssociation
                
                # Створюємо асоціацію з угодою
                association = PublicAssociation(
                    _from=hubspot_note_id,
                    to=lead.hubspot_deal_id,
                    type="note_to_deal"
                )
                
                batch_input = BatchInputPublicAssociation(inputs=[association])
                
                hubspot_client.crm.associations.batch_api.create(
                    "notes",
                    "deals",
                    batch_input_public_association=batch_input
                )
                print(f"Нотатку {hubspot_note_id} прив'язано до угоди {lead.hubspot_deal_id}")
            except Exception as assoc_error:
                print(f"Помилка прив'язки нотатки до угоди: {assoc_error}")
        
        return True
        
    except Exception as e:
        print(f"Помилка створення нотатки в HubSpot: {e}")
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
                "email", "phone", "phone_number", "firstname", "lastname", "notes_last_contacted", "hs_last_activity_date",
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
            
            # Оновлюємо основний телефон (спочатку phone_number, потім phone як fallback)
            if contact.properties.get('phone_number'):
                lead.phone = contact.properties['phone_number']
            elif contact.properties.get('phone'):
                lead.phone = contact.properties['phone']
            
            # Оновлюємо додаткові контактні дані
            if contact.properties.get('phone_number_1'):
                lead.second_phone = contact.properties['phone_number_1']
            
            # Мапимо telegram (спочатку з __cloned_, потім без)
            if contact.properties.get('telegram__cloned_'):
                lead.telegram_nickname = contact.properties['telegram__cloned_']
                print(f"Оновлено telegram з контакту (__cloned_): {contact.properties['telegram__cloned_']}")
            elif contact.properties.get('telegram'):
                lead.telegram_nickname = contact.properties['telegram']
                print(f"Оновлено telegram з контакту: {contact.properties['telegram']}")
            
            # Мапимо messenger (спочатку з __cloned_, потім без)
            if contact.properties.get('messenger__cloned_'):
                lead.messenger = contact.properties['messenger__cloned_']
                print(f"Оновлено messenger з контакту (__cloned_): {contact.properties['messenger__cloned_']}")
            elif contact.properties.get('messenger'):
                lead.messenger = contact.properties['messenger']
                print(f"Оновлено messenger з контакту: {contact.properties['messenger']}")
            
            # Мапимо birthdate (спочатку з __cloned_, потім без)
            birth_date_value = None
            if contact.properties.get('birthdate__cloned_'):
                birth_date_value = contact.properties['birthdate__cloned_']
            elif contact.properties.get('birthdate'):
                birth_date_value = contact.properties['birthdate']
            
            if birth_date_value:
                try:
                    from datetime import datetime
                    birth_date = datetime.strptime(birth_date_value, '%Y-%m-%d').date()
                    lead.birth_date = birth_date
                    print(f"Оновлено birthdate з контакту: {birth_date_value}")
                except (ValueError, TypeError):
                    print(f"Не вдалося перетворити дату народження з контакту: {birth_date_value}")
            
            if contact.properties.get('company'):
                lead.company = contact.properties['company']
            
            # Оновлюємо нотатки
            if contact.properties.get('notes_last_contacted'):
                # Перевіряємо, чи є вже така нотатка
                existing_note = NoteStatus.query.filter_by(
                    lead_id=lead.id,
                    note_text=contact.properties['notes_last_contacted']
                ).first()
                
                if not existing_note:
                    # Додаємо нову нотатку
                    new_note = NoteStatus(
                        lead_id=lead.id,
                        note_text=contact.properties['notes_last_contacted'],
                        status='read'  # Нотатка з HubSpot вважається прочитаною
                    )
                    db.session.add(new_note)
        
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
                    "responisble_agent"
                ]
            )
            print(f"Отримано угоду з HubSpot: {deal.properties}")
            
            if deal.properties:
                # Оновлюємо статус угоди
                if deal.properties.get('dealstage'):
                    # Мапимо статуси HubSpot на наші статуси
                    stage_mapping = {
                        '3206423796': 'new',  # Новая заявка
                        '3204738255': 'contacted',  # Вовремя не обработан
                        '3204738256': 'qualified',  # Звонок успешный
                        '3204738257': 'closed'  # Закрыт
                    }
                    hubspot_stage = deal.properties['dealstage']
                    if hubspot_stage in stage_mapping:
                        lead.status = stage_mapping[hubspot_stage]
                
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
                
                # Оновлюємо deal owner (власника угоди) - зберігаємо в окремому полі
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
                                # Зберігаємо HubSpot deal owner в notes
                                if not lead.notes or "HubSpot Deal Owner:" not in lead.notes:
                                    lead.notes = f"HubSpot Deal Owner: {owner_name}"
                                print(f"HubSpot власник угоди: {owner_name}")
                    except Exception as e:
                        print(f"Помилка отримання власника угоди: {e}")
        
        # Синхронізуємо нотатки з HubSpot
        sync_notes_from_hubspot(lead)
        
        # Синхронізуємо активності з HubSpot
        sync_activities_from_hubspot(lead)
        
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
                    from datetime import datetime
                    user.last_login = datetime.now()
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
    return render_template('profile.html')

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
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        # Перевіряємо, чи існує користувач з таким ім'ям або email
        existing_user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Користувач з таким ім\'ям або email вже існує')
            return render_template('register.html', form=form)
        
        # Перевіряємо, чи співпадають паролі
        if form.password.data != form.confirm_password.data:
            flash('Паролі не співпадають')
            return render_template('register.html', form=form)
        
        try:
            # Створюємо нового користувача (за замовчуванням - агент)
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                role='agent'  # За замовчуванням всі нові користувачі - агенти
            )
            new_user.set_password(form.password.data)
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Реєстрація успішна! Тепер ви можете увійти в систему.')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Помилка при реєстрації: {str(e)}')
    
    return render_template('register.html', form=form)

@app.route('/request_verification', methods=['POST'])
@login_required
def request_verification():
    """Запит на верифікацію від агента"""
    if current_user.role == 'admin':
        return jsonify({'success': False, 'message': 'Адміністратори не потребують верифікації'})
    
    if current_user.verification_requested:
        return jsonify({'success': False, 'message': 'Ви вже подавали запит на верифікацію'})
    
    try:
        from datetime import datetime
        current_user.verification_requested = True
        current_user.verification_request_date = datetime.now()
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
        lead.notes = (lead.notes or '') + f'\n[Угода закрита {datetime.now().strftime("%d.%m.%Y %H:%M")}]'
        
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
        NoteStatus.query.filter_by(lead_id=lead_id).delete()
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
    
    try:
        agent = User.query.get(agent_id)
        if not agent or agent.role != 'agent':
            return jsonify({'success': False, 'message': 'Агент не знайдено'})
        
        if approve:
            agent.is_verified = True
            agent.verification_requested = False
            message = f'Агент {agent.username} успішно верифікований'
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
    # Автоматична синхронізація з HubSpot при завантаженні дашборду
    if hubspot_client:
        try:
            sync_all_leads_from_hubspot()
        except Exception as e:
            print(f"Помилка автоматичної синхронізації: {e}")
    
    if current_user.role == 'admin':
        leads = Lead.query.all()
    else:
        leads = Lead.query.filter_by(agent_id=current_user.id).all()
    
    # Обчислюємо метрики
    total_leads = len(leads)
    active_leads = len([lead for lead in leads if lead.status in ['new', 'contacted', 'qualified']])
    closed_leads = len([lead for lead in leads if lead.status == 'closed'])
    transferred_leads = len([lead for lead in leads if lead.is_transferred])
    
    # Сума всіх бюджетів
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
    
    return render_template('dashboard.html', leads=leads, metrics=metrics)

@app.route('/add_lead', methods=['GET', 'POST'])
@login_required
def add_lead():
    form = LeadForm(request.form)
    
    # Встановлюємо agent_id для поточного користувача
    if current_user.role == 'agent':
        form.agent_id.data = current_user.id
    elif current_user.role == 'admin':
        # Для адміна можна вибрати агента, але за замовчуванням - поточний користувач
        form.agent_id.data = current_user.id
    
    if request.method == 'POST' and form.validate():
        try:
            # Валідація та форматування телефону
            phone_number = form.phone.data
            try:
                parsed_number = phonenumbers.parse(phone_number, None)
                if not phonenumbers.is_valid_number(parsed_number):
                    return redirect(url_for('add_lead', flash='Невірний формат номера телефону', type='error'))
                formatted_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            except phonenumbers.NumberParseException:
                return redirect(url_for('add_lead', flash='Невірний формат номера телефону', type='error'))
            
            # Ініціалізуємо HubSpot ID як None
            hubspot_contact_id = None
            hubspot_deal_id = None
            
            # Спробуємо створити в HubSpot (якщо API налаштований)
            if hubspot_client:
                print(f"Створюємо контакт в HubSpot для {form.email.data}")
                try:
                    # Перевіряємо, чи існує контакт з таким email
                    from hubspot.crm.contacts import SimplePublicObjectInput
                    
                    try:
                        # Шукаємо існуючий контакт за email
                        existing_contacts = hubspot_client.crm.contacts.search_api.do_search(
                            query=form.email.data,
                            properties=["email", "firstname", "lastname"],
                            limit=1
                        )
                        print(f"Пошук контакту за email {form.email.data}: знайдено {len(existing_contacts.results)} контактів")
                        
                        if existing_contacts.results:
                            # Контакт існує, використовуємо його
                            hubspot_contact_id = str(existing_contacts.results[0].id)
                            print(f"Використовуємо існуючий HubSpot контакт: {hubspot_contact_id}")
                        else:
                            # Контакт не існує, створюємо новий
                            print(f"Контакт не знайдено, створюємо новий для {form.email.data}")
                            contact_properties = {
                                "email": form.email.data,
                                "phone": formatted_phone,
                                "firstname": form.deal_name.data.split()[0] if form.deal_name.data.split() else "Lead",
                                "lastname": " ".join(form.deal_name.data.split()[1:]) if len(form.deal_name.data.split()) > 1 else "Client"
                            }
                            
                            contact_input = SimplePublicObjectInput(properties=contact_properties)
                            hubspot_contact = hubspot_client.crm.contacts.basic_api.create(simple_public_object_input=contact_input)
                            hubspot_contact_id = str(hubspot_contact.id)
                            print(f"HubSpot контакт створено: {hubspot_contact_id}")
                            
                    except Exception as search_error:
                        print(f"Помилка пошуку контакту: {search_error}")
                        # Якщо пошук не вдався, спробуємо створити контакт
                        try:
                            contact_properties = {
                                "email": form.email.data,
                                "phone": formatted_phone,
                                "firstname": form.deal_name.data.split()[0] if form.deal_name.data.split() else "Lead",
                                "lastname": " ".join(form.deal_name.data.split()[1:]) if len(form.deal_name.data.split()) > 1 else "Client"
                            }
                            
                            contact_input = SimplePublicObjectInput(properties=contact_properties)
                            hubspot_contact = hubspot_client.crm.contacts.basic_api.create(simple_public_object_input=contact_input)
                            hubspot_contact_id = str(hubspot_contact.id)
                            print(f"HubSpot контакт створено: {hubspot_contact_id}")
                        except Exception as create_error:
                            # Якщо контакт вже існує, показуємо помилку
                            if "Contact already exists" in str(create_error):
                                return redirect(url_for('add_lead', flash=f'Контакт з email {form.email.data} вже існує в системі. Будь ласка, використайте інший email або зверніться до адміністратора.', type='error'))
                            else:
                                raise create_error
                    
                    # Створюємо deal в HubSpot
                    print(f"Створюємо угоду в HubSpot: {form.deal_name.data}")
                    from hubspot.crm.deals import SimplePublicObjectInput as DealInput
                    
                    deal_properties = {
                        "dealname": form.deal_name.data,
                        "amount": get_budget_value(form.budget.data),
                        "dealtype": "newbusiness",
                        "pipeline": "2341107958",  # Pipeline ID для "Лиды"
                        "dealstage": "3206423796"  # Стадія ID для "Новая заявка" в pipeline "Лиды"
                    }
                    
                    print(f"Властивості угоди: {deal_properties}")
                    deal_input = DealInput(properties=deal_properties)
                    hubspot_deal = hubspot_client.crm.deals.basic_api.create(simple_public_object_input=deal_input)
                    hubspot_deal_id = str(hubspot_deal.id)
                    print(f"HubSpot угода створено: {hubspot_deal_id}")
                    
                    # Створюємо зв'язок між контактом та угодою
                    try:
                        from hubspot.crm.associations import SimplePublicObjectId
                        
                        # Зв'язуємо контакт з угодою
                        contact_id = SimplePublicObjectId(id=hubspot_contact_id)
                        deal_id = SimplePublicObjectId(id=hubspot_deal_id)
                        
                        hubspot_client.crm.associations.basic_api.create(
                            from_object_type="contacts",
                            from_object_id=hubspot_contact_id,
                            to_object_type="deals", 
                            to_object_id=hubspot_deal_id,
                            association_type="contact_to_deal"
                        )
                        print(f"Зв'язок між контактом {hubspot_contact_id} та угодою {hubspot_deal_id} створено")
                    except Exception as assoc_error:
                        print(f"Помилка створення зв'язку: {assoc_error}")
                    
                except Exception as hubspot_error:
                    print(f"HubSpot помилка: {hubspot_error}")
                    # Якщо контакт вже існує, показуємо помилку
                    if "Contact already exists" in str(hubspot_error):
                        return redirect(url_for('add_lead', flash=f'Контакт з email {form.email.data} вже існує в системі. Будь ласка, використайте інший email або зверніться до адміністратора.', type='error'))
                    else:
                        return redirect(url_for('add_lead', flash='Лід додано локально. Помилка синхронізації з HubSpot.', type='warning'))
            else:
                print("HubSpot клієнт не налаштований")
                return redirect(url_for('add_lead', flash='Лід додано локально. HubSpot API не налаштований.', type='warning'))
            
            # Зберігаємо лід в локальній базі
            lead = Lead(
                agent_id=current_user.id,
                deal_name=form.deal_name.data,
                email=form.email.data,
                phone=formatted_phone,
                budget=form.budget.data,
                notes=form.notes.data,
                hubspot_contact_id=hubspot_contact_id,
                hubspot_deal_id=hubspot_deal_id
            )
            
            db.session.add(lead)
            
            # Нараховуємо поінти за створення ліда
            agent = User.query.get(form.agent_id.data)
            if agent:
                agent.add_points(100)  # 100 поінтів за лід
                agent.total_leads += 1
                print(f"Нараховано 100 поінтів агенту {agent.username} за створення ліда")
            
            db.session.commit()
            
            if hubspot_contact_id:
                return redirect(url_for('dashboard', flash='Лід успішно додано та синхронізовано з HubSpot!', type='success'))
            else:
                return redirect(url_for('dashboard', flash='Лід успішно додано локально!', type='success'))
            
        except Exception as e:
            return redirect(url_for('add_lead', flash=f'Помилка при додаванні ліда: {str(e)}', type='error'))
    
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


@app.route('/update_note_status/<int:note_id>', methods=['POST'])
@login_required
def update_note_status(note_id):
    note = NoteStatus.query.get_or_404(note_id)
    lead = Lead.query.get_or_404(note.lead_id)
    
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'У вас немає прав для редагування цієї нотатки'})
    
    new_status = request.json.get('status')
    if new_status not in ['sent', 'read', 'replied']:
        return jsonify({'success': False, 'message': 'Невірний статус'})
    
    note.status = new_status
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Статус нотатки оновлено',
        'new_status': new_status
    })

@app.route('/lead/<int:lead_id>')
@login_required
def view_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if lead.agent_id != current_user.id and current_user.role != 'admin':
        flash('У вас немає прав для перегляду цього ліда')
        return redirect(url_for('dashboard'))
    
    # Синхронізуємо конкретний лід з HubSpot
    if hubspot_client:
        try:
            sync_lead_from_hubspot(lead)
        except Exception as e:
            print(f"Помилка синхронізації ліда {lead_id}: {e}")
    
    agent = User.query.get(lead.agent_id)
    try:
        notes = NoteStatus.query.filter_by(lead_id=lead.id).order_by(NoteStatus.created_at.desc()).all()
    except Exception:
        # Якщо таблиця note_status не існує, використовуємо старі нотатки з поля notes
        notes = []
    
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
        
        flash('Лід успішно оновлено!')
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
    """Ручна синхронізація всіх лідів з HubSpot"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Тільки адміністратор може синхронізувати всі ліді'})
    
    if not hubspot_client:
        return jsonify({'success': False, 'message': 'HubSpot API не налаштований'})
    
    try:
        success = sync_all_leads_from_hubspot()
        if success:
            return jsonify({'success': True, 'message': 'Всі ліді успішно синхронізовано з HubSpot'})
        else:
            return jsonify({'success': False, 'message': 'Помилка синхронізації з HubSpot'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

@app.route('/add_note/<int:lead_id>', methods=['POST'])
@login_required
def add_note(lead_id):
    """API endpoint для додавання нотатки до ліда"""
    lead = Lead.query.get_or_404(lead_id)
    
    # Перевіряємо доступ до ліда
    if current_user.role == 'agent' and lead.agent_id != current_user.id:
        return jsonify({'success': False, 'message': 'Доступ заборонено'}), 403
    
    data = request.get_json()
    note_text = data.get('note_text', '').strip()
    
    if not note_text:
        return jsonify({'success': False, 'message': 'Текст нотатки не може бути порожнім'}), 400
    
    try:
        # Створюємо нотатку в локальній БД
        new_note = NoteStatus(
            lead_id=lead.id,
            note_text=note_text,
            status='read'
        )
        db.session.add(new_note)
        
        # Створюємо нотатку в HubSpot
        hubspot_success = create_note_in_hubspot(lead, note_text)
        
        if hubspot_success:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Нотатку додано та синхронізовано з HubSpot',
                'note_id': new_note.id
            })
        else:
            # Якщо HubSpot не працює, все одно зберігаємо локально
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Нотатку додано локально (HubSpot недоступний)',
                'note_id': new_note.id
            })
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Помилка: {str(e)}'}), 500

@app.route('/admin/users')
@login_required
def admin_users():
    """Адмін-панель управління користувачами"""
    if current_user.role != 'admin':
        flash('Доступ заборонено')
        return redirect(url_for('dashboard'))
    
    # Отримуємо всіх користувачів (сортуємо за датою створення, найновіші зверху)
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Створюємо таблицю для нотаток, якщо вона не існує
        try:
            NoteStatus.query.first()
        except:
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
    
    app.run(debug=True)
