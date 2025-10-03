"""
Pytest конфігурація та фікстури для ProPart Real Estate Hub
"""
import os
import tempfile
import pytest
from datetime import datetime, timedelta
from flask import Flask
from werkzeug.security import generate_password_hash

# Додаємо батьківську директорію до шляху Python
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session')
def test_app():
    """Створює тестовий Flask додаток"""
    from .test_app import create_test_app
    
    app, db, User, Lead, NoteStatus, Activity = create_test_app()
    
    with app.app_context():
        db.create_all()
        yield app, db, User, Lead, NoteStatus, Activity
        db.drop_all()


@pytest.fixture
def init_db(test_app):
    """Ініціалізує базу даних для тестів"""
    app, db, User, Lead, NoteStatus, Activity = test_app
    
    with app.app_context():
        db.create_all()
        yield db, User, Lead, NoteStatus, Activity
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user_data():
    """Тестові дані для користувача"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpassword123',
        'role': 'agent'
    }


@pytest.fixture
def sample_admin_data():
    """Тестові дані для адміністратора"""
    return {
        'username': 'testadmin',
        'email': 'admin@example.com',
        'password': 'adminpassword123',
        'role': 'admin'
    }


@pytest.fixture
def sample_lead_data():
    """Тестові дані для ліда"""
    return {
        'deal_name': 'Test Lead',
        'email': 'lead@example.com',
        'phone': '+380501234567',
        'budget': '200к–500к',
        'status': 'new',
        'notes': 'Test lead notes'
    }


@pytest.fixture
def create_test_user(init_db, sample_user_data):
    """Створює тестового користувача"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    user = User(
        username=sample_user_data['username'],
        email=sample_user_data['email'],
        role=sample_user_data['role']
    )
    user.set_password(sample_user_data['password'])
    
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def create_test_admin(init_db, sample_admin_data):
    """Створює тестового адміністратора"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    admin = User(
        username=sample_admin_data['username'],
        email=sample_admin_data['email'],
        role=sample_admin_data['role']
    )
    admin.set_password(sample_admin_data['password'])
    
    db.session.add(admin)
    db.session.commit()
    return admin


@pytest.fixture
def create_test_lead(init_db, create_test_user, sample_lead_data):
    """Створює тестового ліда"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    lead = Lead(
        agent_id=create_test_user.id,
        deal_name=sample_lead_data['deal_name'],
        email=sample_lead_data['email'],
        phone=sample_lead_data['phone'],
        budget=sample_lead_data['budget'],
        status=sample_lead_data['status'],
        notes=sample_lead_data['notes']
    )
    
    db.session.add(lead)
    db.session.commit()
    return lead


@pytest.fixture
def create_test_note(init_db, create_test_lead):
    """Створює тестову нотатку"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    note = NoteStatus(
        lead_id=create_test_lead.id,
        note_text='Test note content',
        status='sent'
    )
    
    db.session.add(note)
    db.session.commit()
    return note


@pytest.fixture
def create_test_activity(init_db, create_test_lead):
    """Створює тестову активність"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    activity = Activity(
        lead_id=create_test_lead.id,
        activity_type='email',
        subject='Test email subject',
        body='Test email body',
        status='completed',
        direction='outbound'
    )
    
    db.session.add(activity)
    db.session.commit()
    return activity


@pytest.fixture
def multiple_users(init_db):
    """Створює кілька тестових користувачів"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    users = []
    for i in range(3):
        user = User(
            username=f'testuser{i}',
            email=f'test{i}@example.com',
            role='agent'
        )
        user.set_password('password123')
        db.session.add(user)
        users.append(user)
    
    db.session.commit()
    return users


@pytest.fixture
def multiple_leads(init_db, multiple_users):
    """Створює кілька тестових лідів"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    leads = []
    for i, user in enumerate(multiple_users):
        lead = Lead(
            agent_id=user.id,
            deal_name=f'Test Lead {i}',
            email=f'lead{i}@example.com',
            phone=f'+38050123456{i}',
            budget='200к–500к',
            status='new'
        )
        db.session.add(lead)
        leads.append(lead)
    
    db.session.commit()
    return leads


@pytest.fixture
def frozen_time():
    """Фікстура для тестування з фіксованим часом"""
    from freezegun import freeze_time
    with freeze_time("2024-01-15 12:00:00"):
        yield


@pytest.fixture
def mock_hubspot_client(monkeypatch):
    """Мокує HubSpot клієнт для тестів"""
    class MockHubSpotClient:
        def __init__(self, *args, **kwargs):
            pass
        
        def crm(self):
            return self
        
        def contacts(self):
            return self
        
        def deals(self):
            return self
        
        def basic_api(self):
            return self
        
        def create(self, *args, **kwargs):
            class MockResult:
                id = 'test_hubspot_id'
                properties = {'test': 'value'}
            return MockResult()
        
        def get_by_id(self, *args, **kwargs):
            class MockResult:
                properties = {'test': 'value'}
            return MockResult()
        
        def search_api(self):
            return self
        
        def do_search(self, *args, **kwargs):
            class MockResult:
                results = []
            return MockResult()
    
    monkeypatch.setattr('app.hubspot_client', MockHubSpotClient())
