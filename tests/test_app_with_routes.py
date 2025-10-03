"""
Тестовий Flask додаток з маршрутами для тестування веб-інтерфейсу
"""
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email
from werkzeug.exceptions import NotFound, InternalServerError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_app_with_routes():
    """Створює тестовий Flask додаток з маршрутами"""
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'WTF_CSRF_ENABLED': False,
        'HUBSPOT_API_KEY': None,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_pre_ping': True,
        }
    })

    db = SQLAlchemy(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    bcrypt = Bcrypt(app)
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["1000 per day"],
        storage_uri="memory://"
    )
    
    # Мокаємо HubSpot клієнт для тестів
    hubspot_client = None

    # Моделі
    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False)
        password_hash = db.Column(db.String(255), nullable=False)
        role = db.Column(db.String(20), default='agent')
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
        verification_document_path = db.Column(db.String(200))
        verification_notes = db.Column(db.Text)
        
        # Статус акаунту
        is_active = db.Column(db.Boolean, default=True)
        last_login = db.Column(db.DateTime)
        login_attempts = db.Column(db.Integer, default=0)
        locked_until = db.Column(db.DateTime)
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if self.points is None: self.points = 0
            if self.level is None: self.level = 'bronze'
            if self.total_leads is None: self.total_leads = 0
            if self.closed_deals is None: self.closed_deals = 0
            if self.is_verified is None: self.is_verified = False
            if self.verification_requested is None: self.verification_requested = False
            if self.is_active is None: self.is_active = True
            if self.login_attempts is None: self.login_attempts = 0

        def set_password(self, password):
            self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        def check_password(self, password):
            if self.password_hash.startswith('$2b$') or self.password_hash.startswith('$2a$'):
                return bcrypt.check_password_hash(self.password_hash, password)
            else:
                from werkzeug.security import check_password_hash
                return check_password_hash(self.password_hash, password)
        
        def update_level(self):
            if self.points >= 10000:
                self.level = 'platinum'
            elif self.points >= 5000:
                self.level = 'gold'
            elif self.points >= 2000:
                self.level = 'silver'
            else:
                self.level = 'bronze'
        
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
            self.unlock_account()

    class Lead(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        deal_name = db.Column(db.String(100), nullable=False)
        email = db.Column(db.String(120), nullable=False)
        phone = db.Column(db.String(20))
        budget = db.Column(db.String(50))
        status = db.Column(db.String(50), default='new')
        is_transferred = db.Column(db.Boolean, default=False)
        notes = db.Column(db.Text)
        last_updated_hubspot = db.Column(db.DateTime)
        
        # Додаткові поля
        country = db.Column(db.String(50))
        purchase_goal = db.Column(db.String(50))
        property_type = db.Column(db.String(50))
        object_type = db.Column(db.String(50))
        communication_language = db.Column(db.String(50))
        source = db.Column(db.String(50))
        refusal_reason = db.Column(db.String(50))
        
        # Контактні дані
        company = db.Column(db.String(100))
        second_phone = db.Column(db.String(20))
        telegram_nickname = db.Column(db.String(50))
        messenger = db.Column(db.String(20))
        birth_date = db.Column(db.Date)
        
        hubspot_contact_id = db.Column(db.String(50))
        hubspot_deal_id = db.Column(db.String(50))
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if self.status is None: self.status = 'new'
            if self.is_transferred is None: self.is_transferred = False

    class NoteStatus(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
        note_text = db.Column(db.Text, nullable=False)
        status = db.Column(db.String(50), default='sent')
        created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
        updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if self.status is None: self.status = 'sent'

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
            if self.status is None: self.status = 'completed'

    # Форми
    class LoginForm(FlaskForm):
        username = StringField('Ім\'я користувача', [DataRequired(), Length(min=4, max=25)])
        password = PasswordField('Пароль', [DataRequired()])

    class RegistrationForm(FlaskForm):
        username = StringField('Ім\'я користувача', [DataRequired(), Length(min=4, max=25)])
        email = StringField('Email', [DataRequired(), Email()])
        password = PasswordField('Пароль', [DataRequired(), Length(min=6)])
        confirm_password = PasswordField('Підтвердіть пароль', [DataRequired()])

    class LeadForm(FlaskForm):
        deal_name = StringField('Deal name', [DataRequired(), Length(min=2, max=100)])
        email = StringField('Email', [DataRequired(), Email()])
        phone = StringField('Phone number', [DataRequired(), Length(max=20)])
        budget = SelectField('Budget', choices=[
            ('до 200к', 'до 200к'),
            ('200к–500к', '200к–500к'),
            ('500к–1млн', '500к–1млн'),
            ('1млн+', '1млн+')
        ], validators=[DataRequired()])
        notes = TextAreaField('Примітки', [Length(max=500)])
        agent_id = HiddenField('Agent ID')

    # Login manager
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Маршрути
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                if user.is_account_locked():
                    flash('Акаунт заблокований. Спробуйте пізніше.', 'error')
                    return render_template('login.html', form=form)
                
                login_user(user, remember=True)
                user.last_login = datetime.now()
                user.reset_login_attempts()
                db.session.commit()
                return redirect(url_for('dashboard'))
            else:
                if user:
                    user.increment_login_attempts()
                    db.session.commit()
                flash('Невірне ім\'я користувача або пароль', 'error')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            if form.password.data != form.confirm_password.data:
                flash('Паролі не співпадають', 'error')
                return render_template('register.html', form=form)
            
            if User.query.filter_by(username=form.username.data).first():
                flash('Користувач з таким іменем вже існує', 'error')
                return render_template('register.html', form=form)
            
            if User.query.filter_by(email=form.email.data).first():
                flash('Користувач з таким email вже існує', 'error')
                return render_template('register.html', form=form)
            
            user = User(
                username=form.username.data,
                email=form.email.data,
                role='agent'
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            flash('Реєстрація успішна! Тепер ви можете увійти в систему.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html', form=form)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/profile')
    @login_required
    def profile():
        return render_template('profile.html', user=current_user)

    @app.route('/profile/update', methods=['POST'])
    @login_required
    def update_profile():
        new_email = request.form.get('email')
        new_role = request.form.get('role')
        
        if new_email:
            current_user.email = new_email
        if new_role:
            current_user.role = new_role
        
        db.session.commit()
        flash('Профіль оновлено', 'success')
        return redirect(url_for('profile'))

    @app.route('/api/profile/stats')
    @login_required
    def profile_stats():
        try:
            stats = {
                'total_leads': current_user.total_leads,
                'closed_deals': current_user.closed_deals,
                'points': current_user.points,
                'level': current_user.level
            }
            return jsonify({'success': True, 'stats': stats})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Помилка: {str(e)}'})

    @app.route('/add_lead', methods=['GET', 'POST'])
    @login_required
    def add_lead():
        form = LeadForm()
        if form.validate_on_submit():
            lead = Lead(
                deal_name=form.deal_name.data,
                email=form.email.data,
                phone=form.phone.data,
                budget=form.budget.data,
                notes=form.notes.data,
                agent_id=current_user.id
            )
            db.session.add(lead)
            db.session.commit()
            flash('Лід успішно додано', 'success')
            return redirect(url_for('dashboard'))
        
        return render_template('add_lead.html', form=form)

    @app.route('/lead/<int:lead_id>')
    @login_required
    def view_lead(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        if lead.agent_id != current_user.id and current_user.role != 'admin':
            flash('У вас немає доступу до цього ліда', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('lead_detail.html', lead=lead)

    @app.route('/lead/<int:lead_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_lead(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        if lead.agent_id != current_user.id and current_user.role != 'admin':
            flash('У вас немає доступу до цього ліда', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            lead.deal_name = request.form.get('deal_name', lead.deal_name)
            lead.email = request.form.get('email', lead.email)
            lead.phone = request.form.get('phone', lead.phone)
            lead.budget = request.form.get('budget', lead.budget)
            lead.status = request.form.get('status', lead.status)
            db.session.commit()
            flash('Лід оновлено', 'success')
            return redirect(url_for('view_lead', lead_id=lead.id))
        
        return render_template('edit_lead.html', lead=lead)

    @app.route('/delete_lead/<int:lead_id>', methods=['DELETE'])
    @login_required
    def delete_lead(lead_id):
        lead = Lead.query.get_or_404(lead_id)
        if lead.agent_id != current_user.id and current_user.role != 'admin':
            return jsonify({'error': 'Немає доступу'}), 403
        
        db.session.delete(lead)
        db.session.commit()
        return jsonify({'success': True})

    @app.route('/admin/verification')
    @login_required
    def admin_verification():
        if current_user.role != 'admin':
            flash('У вас немає доступу до цієї сторінки', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('admin_verification.html')

    @app.route('/admin/users')
    @login_required
    def admin_users():
        if current_user.role != 'admin':
            flash('У вас немає доступу до цієї сторінки', 'error')
            return redirect(url_for('dashboard'))
        
        users = User.query.all()
        return render_template('admin_users.html', users=users)

    # Обробка помилок
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', error_code=404, error_message="Сторінка не знайдена"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', error_code=500, error_message="Внутрішня помилка сервера"), 500

    return app, db, User, Lead, NoteStatus, Activity
