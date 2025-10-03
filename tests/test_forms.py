"""
Тести для форм ProPart Real Estate Hub
"""
import pytest
import os
import sys
from datetime import datetime

# Додаємо батьківську директорію до шляху Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .test_app import create_test_app


class TestLoginForm:
    """Тести для форми входу"""
    
    def test_login_form_creation(self, init_db):
        """Тест створення форми входу"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            # Імпортуємо форми з основного додатку
            from app import LoginForm
            
            form = LoginForm()
            assert form is not None
            assert hasattr(form, 'username')
            assert hasattr(form, 'password')
    
    def test_login_form_validation_valid_data(self, init_db):
        """Тест валідації форми з валідними даними"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LoginForm
            
            form = LoginForm(data={
                'username': 'testuser',
                'password': 'password123'
            })
            
            assert form.validate()
            assert form.username.data == 'testuser'
            assert form.password.data == 'password123'
    
    def test_login_form_validation_empty_fields(self, init_db):
        """Тест валідації форми з порожніми полями"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LoginForm
            
            # Тест з порожнім username
            form = LoginForm(data={
                'username': '',
                'password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            
            # Тест з порожнім password
            form = LoginForm(data={
                'username': 'testuser',
                'password': ''
            })
            
            assert not form.validate()
            assert 'password' in form.errors
    
    def test_login_form_validation_username_length(self, init_db):
        """Тест валідації довжини імені користувача"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LoginForm
            
            # Тест з занадто коротким username
            form = LoginForm(data={
                'username': 'abc',  # менше 4 символів
                'password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            
            # Тест з занадто довгим username
            form = LoginForm(data={
                'username': 'a' * 26,  # більше 25 символів
                'password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
    
    def test_login_form_field_labels(self, init_db):
        """Тест міток полів форми"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LoginForm
            
            form = LoginForm()
            assert form.username.label.text == "Ім'я користувача"
            assert form.password.label.text == "Пароль"


class TestLeadForm:
    """Тести для форми створення ліда"""
    
    def test_lead_form_creation(self, init_db):
        """Тест створення форми ліда"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            form = LeadForm()
            assert form is not None
            assert hasattr(form, 'deal_name')
            assert hasattr(form, 'email')
            assert hasattr(form, 'phone')
            assert hasattr(form, 'budget')
            assert hasattr(form, 'notes')
            assert hasattr(form, 'agent_id')
    
    def test_lead_form_validation_valid_data(self, init_db):
        """Тест валідації форми з валідними даними"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'notes': 'Interested in apartment',
                'agent_id': '1'
            })
            
            assert form.validate()
            assert form.deal_name.data == 'John Doe Deal'
            assert form.email.data == 'john@example.com'
            assert form.phone.data == '+1234567890'
            assert form.budget.data == '200к–500к'
            assert form.notes.data == 'Interested in apartment'
            assert form.agent_id.data == '1'
    
    def test_lead_form_validation_required_fields(self, init_db):
        """Тест валідації обов'язкових полів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            # Тест з порожнім deal_name
            form = LeadForm(data={
                'deal_name': '',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'deal_name' in form.errors
            
            # Тест з порожнім email
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': '',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'email' in form.errors
            
            # Тест з порожнім phone
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '',
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'phone' in form.errors
            
            # Тест з порожнім budget
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': ''
            })
            
            assert not form.validate()
            assert 'budget' in form.errors
    
    def test_lead_form_validation_email_format(self, init_db):
        """Тест валідації формату email"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            # Тест з невалідним email
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'invalid-email',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'email' in form.errors
            
            # Тест з валідним email
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john.doe@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert form.validate()
    
    def test_lead_form_validation_field_lengths(self, init_db):
        """Тест валідації довжини полів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            # Тест з занадто коротким deal_name
            form = LeadForm(data={
                'deal_name': 'A',  # менше 2 символів
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'deal_name' in form.errors
            
            # Тест з занадто довгим deal_name
            form = LeadForm(data={
                'deal_name': 'A' * 101,  # більше 100 символів
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'deal_name' in form.errors
            
            # Тест з занадто довгим phone
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+123456789012345678901',  # більше 20 символів
                'budget': '200к–500к'
            })
            
            assert not form.validate()
            assert 'phone' in form.errors
            
            # Тест з занадто довгими notes
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'notes': 'A' * 501  # більше 500 символів
            })
            
            assert not form.validate()
            assert 'notes' in form.errors
    
    def test_lead_form_budget_choices(self, init_db):
        """Тест вибору бюджету"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            form = LeadForm()
            budget_choices = form.budget.choices
            
            expected_choices = [
                ('до 200к', 'до 200к'),
                ('200к–500к', '200к–500к'),
                ('500к–1млн', '500к–1млн'),
                ('1млн+', '1млн+')
            ]
            
            assert budget_choices == expected_choices
    
    def test_lead_form_optional_notes(self, init_db):
        """Тест опціонального поля notes"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            # Тест без notes (має бути валідним)
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к'
            })
            
            assert form.validate()
            assert form.notes.data is None or form.notes.data == ''
    
    def test_lead_form_hidden_agent_id(self, init_db):
        """Тест прихованого поля agent_id"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadForm
            
            form = LeadForm()
            assert form.agent_id.type == 'HiddenField'
            
            # Тест з agent_id
            form = LeadForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'agent_id': '123'
            })
            
            assert form.validate()
            assert form.agent_id.data == '123'


class TestNoteForm:
    """Тести для форми нотатки"""
    
    def test_note_form_creation(self, init_db):
        """Тест створення форми нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import NoteForm
            
            form = NoteForm()
            assert form is not None
            assert hasattr(form, 'note_text')
    
    def test_note_form_validation_valid_data(self, init_db):
        """Тест валідації форми з валідними даними"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import NoteForm
            
            form = NoteForm(data={
                'note_text': 'This is a valid note'
            })
            
            assert form.validate()
            assert form.note_text.data == 'This is a valid note'
    
    def test_note_form_validation_empty_note(self, init_db):
        """Тест валідації з порожньою нотаткою"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import NoteForm
            
            form = NoteForm(data={
                'note_text': ''
            })
            
            assert not form.validate()
            assert 'note_text' in form.errors
    
    def test_note_form_validation_note_length(self, init_db):
        """Тест валідації довжини нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import NoteForm
            
            # Тест з занадто довгою нотаткою
            form = NoteForm(data={
                'note_text': 'A' * 1001  # більше 1000 символів
            })
            
            assert not form.validate()
            assert 'note_text' in form.errors
            
            # Тест з максимально дозволеною довжиною
            form = NoteForm(data={
                'note_text': 'A' * 1000  # рівно 1000 символів
            })
            
            assert form.validate()
    
    def test_note_form_field_label(self, init_db):
        """Тест мітки поля форми"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import NoteForm
            
            form = NoteForm()
            assert form.note_text.label.text == "Нотатка"


class TestRegistrationForm:
    """Тести для форми реєстрації"""
    
    def test_registration_form_creation(self, init_db):
        """Тест створення форми реєстрації"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            form = RegistrationForm()
            assert form is not None
            assert hasattr(form, 'username')
            assert hasattr(form, 'email')
            assert hasattr(form, 'password')
            assert hasattr(form, 'confirm_password')
    
    def test_registration_form_validation_valid_data(self, init_db):
        """Тест валідації форми з валідними даними"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert form.validate()
            assert form.username.data == 'testuser'
            assert form.email.data == 'test@example.com'
            assert form.password.data == 'password123'
            assert form.confirm_password.data == 'password123'
    
    def test_registration_form_validation_required_fields(self, init_db):
        """Тест валідації обов'язкових полів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            # Тест з порожнім username
            form = RegistrationForm(data={
                'username': '',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            
            # Тест з порожнім email
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': '',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'email' in form.errors
            
            # Тест з порожнім password
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': '',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'password' in form.errors
            
            # Тест з порожнім confirm_password
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': ''
            })
            
            assert not form.validate()
            assert 'confirm_password' in form.errors
    
    def test_registration_form_validation_password_length(self, init_db):
        """Тест валідації довжини пароля"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            # Тест з занадто коротким паролем
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': '12345',  # менше 6 символів
                'confirm_password': '12345'
            })
            
            assert not form.validate()
            assert 'password' in form.errors
    
    def test_registration_form_username_validation(self, init_db):
        """Тест валідації імені користувача"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            # Тест з великими літерами в username
            form = RegistrationForm(data={
                'username': 'TestUser',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            assert 'великі літери' in str(form.username.errors[0])
            
            # Тест з недозволеними символами
            form = RegistrationForm(data={
                'username': 'test-user!',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            
            # Тест з username що починається з цифри
            form = RegistrationForm(data={
                'username': '123test',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            assert 'цифри' in str(form.username.errors[0])
    
    def test_registration_form_username_space_replacement(self, init_db):
        """Тест заміни пробілів на підкреслення в username"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            form = RegistrationForm(data={
                'username': 'test user',
                'email': 'test@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            # Валідуємо форму, щоб спрацювала заміна пробілів
            form.validate()
            
            # Пробіли повинні бути замінені на підкреслення
            assert form.username.data == 'test_user'
    
    def test_registration_form_email_validation(self, init_db):
        """Тест валідації email"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            # Тест з невалідним email
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': 'invalid-email',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert not form.validate()
            assert 'email' in form.errors
            
            # Тест з валідним email
            form = RegistrationForm(data={
                'username': 'testuser',
                'email': 'test.user@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert form.validate()
    
    def test_registration_form_field_labels(self, init_db):
        """Тест міток полів форми"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import RegistrationForm
            
            form = RegistrationForm()
            assert form.username.label.text == "Ім'я користувача"
            assert form.email.label.text == "Email"
            assert form.password.label.text == "Пароль"
            assert form.confirm_password.label.text == "Підтвердіть пароль"


class TestUserEditForm:
    """Тести для форми редагування користувача"""
    
    def test_user_edit_form_creation(self, init_db):
        """Тест створення форми редагування користувача"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import UserEditForm
            
            form = UserEditForm()
            assert form is not None
            assert hasattr(form, 'username')
            assert hasattr(form, 'email')
            assert hasattr(form, 'role')
            assert hasattr(form, 'is_active')
    
    def test_user_edit_form_validation_valid_data(self, init_db):
        """Тест валідації форми з валідними даними"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import UserEditForm
            
            form = UserEditForm(data={
                'username': 'testuser',
                'email': 'test@example.com',
                'role': 'agent',
                'is_active': True
            })
            
            assert form.validate()
            assert form.username.data == 'testuser'
            assert form.email.data == 'test@example.com'
            assert form.role.data == 'agent'
            assert form.is_active.data == True
    
    def test_user_edit_form_role_choices(self, init_db):
        """Тест вибору ролі"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import UserEditForm
            
            form = UserEditForm()
            role_choices = form.role.choices
            
            expected_choices = [
                ('agent', 'Агент'),
                ('admin', 'Адміністратор')
            ]
            
            assert role_choices == expected_choices
    
    def test_user_edit_form_status_choices(self, init_db):
        """Тест вибору статусу"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import UserEditForm
            
            form = UserEditForm()
            status_choices = form.is_active.choices
            
            expected_choices = [
                (True, 'Активний'),
                (False, 'Деактивований')
            ]
            
            assert status_choices == expected_choices
    
    def test_user_edit_form_validation_required_fields(self, init_db):
        """Тест валідації обов'язкових полів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import UserEditForm
            
            # Тест з порожнім username
            form = UserEditForm(data={
                'username': '',
                'email': 'test@example.com',
                'role': 'agent',
                'is_active': True
            })
            
            assert not form.validate()
            assert 'username' in form.errors
            
            # Тест з порожнім email
            form = UserEditForm(data={
                'username': 'testuser',
                'email': '',
                'role': 'agent',
                'is_active': True
            })
            
            assert not form.validate()
            assert 'email' in form.errors
            
            # Тест з порожнім role
            form = UserEditForm(data={
                'username': 'testuser',
                'email': 'test@example.com',
                'role': '',
                'is_active': True
            })
            
            assert not form.validate()
            assert 'role' in form.errors
    
    def test_user_edit_form_email_validation(self, init_db):
        """Тест валідації email"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import UserEditForm
            
            # Тест з невалідним email
            form = UserEditForm(data={
                'username': 'testuser',
                'email': 'invalid-email',
                'role': 'agent',
                'is_active': True
            })
            
            assert not form.validate()
            assert 'email' in form.errors


class TestLeadEditForm:
    """Тести для форми редагування ліда"""
    
    def test_lead_edit_form_creation(self, init_db):
        """Тест створення форми редагування ліда"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            form = LeadEditForm()
            assert form is not None
            assert hasattr(form, 'deal_name')
            assert hasattr(form, 'email')
            assert hasattr(form, 'phone')
            assert hasattr(form, 'budget')
            assert hasattr(form, 'status')
    
    def test_lead_edit_form_validation_valid_data(self, init_db):
        """Тест валідації форми з валідними даними"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            form = LeadEditForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'status': 'new',
                'country': 'Дубай',
                'purchase_goal': 'для себя',
                'property_type': 'офф-план',
                'object_type': 'апартаменты',
                'communication_language': 'украинский',
                'source': 'блогер-агент',
                'refusal_reason': 'недостаточный бюджет',
                'messenger': 'telegram'
            })
            
            assert form.validate(), f"Validation failed: {form.errors}"
            assert form.deal_name.data == 'John Doe Deal'
            assert form.email.data == 'john@example.com'
            assert form.phone.data == '+1234567890'
            assert form.budget.data == '200к–500к'
            assert form.status.data == 'new'
    
    def test_lead_edit_form_budget_choices(self, init_db):
        """Тест вибору бюджету"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            form = LeadEditForm()
            budget_choices = form.budget.choices
            
            expected_choices = [
                ('', 'Оберіть бюджет'),
                ('до 200к', 'до 200к'),
                ('200к–500к', '200к–500к'),
                ('500к–1млн', '500к–1млн'),
                ('1млн+', '1млн+')
            ]
            
            assert budget_choices == expected_choices
    
    def test_lead_edit_form_status_choices(self, init_db):
        """Тест вибору статусу"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            form = LeadEditForm()
            status_choices = form.status.choices
            
            expected_choices = [
                ('new', 'Нова заявка'),
                ('contacted', 'На зв\'язку'),
                ('qualified', 'Кваліфікований'),
                ('closed', 'Закритий')
            ]
            
            assert status_choices == expected_choices
    
    def test_lead_edit_form_validation_required_fields(self, init_db):
        """Тест валідації обов'язкових полів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            # Тест з порожнім deal_name
            form = LeadEditForm(data={
                'deal_name': '',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'status': 'new'
            })
            
            assert not form.validate()
            assert 'deal_name' in form.errors
            
            # Тест з порожнім email
            form = LeadEditForm(data={
                'deal_name': 'John Doe Deal',
                'email': '',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'status': 'new'
            })
            
            assert not form.validate()
            assert 'email' in form.errors
            
            # Тест з порожнім phone
            form = LeadEditForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '',
                'budget': '200к–500к',
                'status': 'new'
            })
            
            assert not form.validate()
            assert 'phone' in form.errors
    
    def test_lead_edit_form_optional_fields(self, init_db):
        """Тест опціональних полів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            # Тест з порожніми опціональними полями (має бути валідним)
            form = LeadEditForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'budget': '',
                'status': 'new',
                'country': '',
                'purchase_goal': '',
                'property_type': '',
                'object_type': '',
                'communication_language': '',
                'source': '',
                'refusal_reason': '',
                'messenger': ''
            })
            
            assert form.validate(), f"Validation failed: {form.errors}"
            assert form.budget.data == ''
            assert form.status.data == 'new'
    
    def test_lead_edit_form_email_validation(self, init_db):
        """Тест валідації email"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app()
        with app.app_context():
            from app import LeadEditForm
            
            # Тест з невалідним email
            form = LeadEditForm(data={
                'deal_name': 'John Doe Deal',
                'email': 'invalid-email',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'status': 'new'
            })
            
            assert not form.validate()
            assert 'email' in form.errors
