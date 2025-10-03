"""
Тестовий Flask додаток для ProPart Real Estate Hub
"""
import os
import sys
from datetime import datetime, timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Додаємо батьківську директорію до шляху Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_app():
    """Створює тестовий Flask додаток"""
    app = Flask(__name__)
    
    # Тестова конфігурація
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'WTF_CSRF_ENABLED': False,
        'HUBSPOT_API_KEY': None,  # Вимкнено для тестів
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_pre_ping': True,
        }
    })
    
    # Ініціалізуємо розширення
    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    bcrypt = Bcrypt(app)
    
    # Rate limiter для тестів
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day"],  # Високий ліміт для тестів
        storage_uri="memory://"
    )
    
    # Створюємо моделі для тестів (копії з основного додатку)
    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(120), nullable=False)
        role = db.Column(db.String(20), nullable=False, default='agent')
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        
        # Геймифікація
        points = db.Column(db.Integer, default=0)
        level = db.Column(db.String(20), default='bronze')
        total_leads = db.Column(db.Integer, default=0)
        closed_deals = db.Column(db.Integer, default=0)
        
        # Верифікація
        is_verified = db.Column(db.Boolean, default=False)
        verification_requested = db.Column(db.Boolean, default=False)
        verification_request_date = db.Column(db.DateTime)
        verification_document_path = db.Column(db.String(255))
        verification_notes = db.Column(db.Text)
        
        # Безпека
        is_active = db.Column(db.Boolean, default=True)
        last_login = db.Column(db.DateTime)
        login_attempts = db.Column(db.Integer, default=0)
        locked_until = db.Column(db.DateTime)
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Встановлюємо значення за замовчуванням
            if self.points is None:
                self.points = 0
            if self.level is None:
                self.level = 'bronze'
            if self.total_leads is None:
                self.total_leads = 0
            if self.closed_deals is None:
                self.closed_deals = 0
            if self.is_verified is None:
                self.is_verified = False
            if self.verification_requested is None:
                self.verification_requested = False
            if self.is_active is None:
                self.is_active = True
            if self.login_attempts is None:
                self.login_attempts = 0
        
        def set_password(self, password):
            self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        def check_password(self, password):
            # Перевіряємо bcrypt hash
            if self.password_hash.startswith('$2b$') or self.password_hash.startswith('$2a$'):
                return bcrypt.check_password_hash(self.password_hash, password)
            # Перевіряємо Werkzeug hash (для сумісності)
            else:
                from werkzeug.security import check_password_hash
                return check_password_hash(self.password_hash, password)
        
        def add_points(self, points):
            self.points += points
            self.update_level()
        
        def update_level(self):
            if self.points >= 10000:
                self.level = 'platinum'
            elif self.points >= 5000:
                self.level = 'gold'
            elif self.points >= 2000:
                self.level = 'silver'
            else:
                self.level = 'bronze'
        
        def get_commission_rate(self):
            rates = {
                'bronze': 5,
                'silver': 7,
                'gold': 10,
                'platinum': 15
            }
            return rates.get(self.level, 5)
        
        def get_level_display_name(self):
            names = {
                'bronze': 'Бронзовий',
                'silver': 'Срібний',
                'gold': 'Золотий',
                'platinum': 'Платиновий'
            }
            return names.get(self.level, 'Бронзовий')
        
        def is_account_locked(self):
            if self.locked_until:
                return datetime.now() < self.locked_until
            return False
        
        def lock_account(self, minutes=30):
            self.locked_until = datetime.now() + timedelta(minutes=minutes)
            self.login_attempts = 0
        
        def unlock_account(self):
            self.locked_until = None
            self.login_attempts = 0
        
        def increment_login_attempts(self):
            self.login_attempts += 1
            if self.login_attempts >= 5:
                self.lock_account()
        
        def reset_login_attempts(self):
            self.login_attempts = 0
            self.unlock_account()  # Розблоковуємо акаунт при скиданні спроб
    
    class Lead(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        deal_name = db.Column(db.String(255), nullable=False)
        email = db.Column(db.String(255), nullable=False)
        phone = db.Column(db.String(50))
        budget = db.Column(db.String(100))
        status = db.Column(db.String(50), default='new')
        is_transferred = db.Column(db.Boolean, default=False)
        notes = db.Column(db.Text)
        last_updated_hubspot = db.Column(db.DateTime)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
        
        # Додаткові поля
        country = db.Column(db.String(100))
        purchase_goal = db.Column(db.String(100))
        property_type = db.Column(db.String(100))
        object_type = db.Column(db.String(100))
        communication_language = db.Column(db.String(50))
        source = db.Column(db.String(100))
        refusal_reason = db.Column(db.Text)
        company = db.Column(db.String(255))
        second_phone = db.Column(db.String(50))
        telegram_nickname = db.Column(db.String(100))
        messenger = db.Column(db.String(50))
        birth_date = db.Column(db.Date)
        hubspot_contact_id = db.Column(db.String(100))
        hubspot_deal_id = db.Column(db.String(100))
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Встановлюємо значення за замовчуванням
            if self.status is None:
                self.status = 'new'
            if self.is_transferred is None:
                self.is_transferred = False
    
    class NoteStatus(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
        note_text = db.Column(db.Text, nullable=False)
        status = db.Column(db.String(50), default='sent')
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Встановлюємо значення за замовчуванням
            if self.status is None:
                self.status = 'sent'
    
    class Activity(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
        hubspot_activity_id = db.Column(db.String(100), unique=True)
        activity_type = db.Column(db.String(50), nullable=False)
        subject = db.Column(db.String(255))
        body = db.Column(db.Text)
        status = db.Column(db.String(50), default='completed')
        direction = db.Column(db.String(50))
        duration = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Встановлюємо значення за замовчуванням
            if self.status is None:
                self.status = 'completed'
    
    return app, db, User, Lead, NoteStatus, Activity
