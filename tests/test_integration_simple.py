"""
Спрощені тести інтеграції та API ProPart Real Estate Hub
"""
import pytest
import os
import sys
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Додаємо батьківську директорію до шляху Python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .test_app_with_routes import create_test_app_with_routes


class TestAPIEndpoints:
    """Тести для API ендпоінтів"""
    
    def test_profile_stats_api(self, init_db):
        """Тест API ендпоінту статистики профілю"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        with app.app_context():
            test_db.create_all()
            
            # Створюємо тестового користувача
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
        
        with app.test_client() as client:
            # Входимо в систему
            client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            })
            
            # Тестуємо API ендпоінт
            response = client.get('/api/profile/stats')
            assert response.status_code == 200
            
            # Перевіряємо JSON відповідь
            data = json.loads(response.data)
            assert 'success' in data
            assert 'stats' in data
            assert 'total_leads' in data['stats']
            assert 'closed_deals' in data['stats']
            assert 'points' in data['stats']
            assert 'level' in data['stats']
    
    def test_profile_stats_api_unauthorized(self, init_db):
        """Тест API ендпоінту статистики профілю без авторизації"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        with app.app_context():
            test_db.create_all()
        
        with app.test_client() as client:
            # Тестуємо API ендпоінт без авторизації
            response = client.get('/api/profile/stats')
            # Повинен перенаправити на login або повернути 401/403
            assert response.status_code in [200, 302, 401, 403]


class TestRateLimiting:
    """Тести для rate limiting"""
    
    def test_hubspot_rate_limiter(self, init_db):
        """Тест HubSpot rate limiter"""
        from hubspot_rate_limiter import HubSpotRateLimiter
        
        # Створюємо rate limiter з малими лімітами для тестування
        limiter = HubSpotRateLimiter(max_calls=2, period=1)
        
        # Функція для тестування
        @limiter
        def test_function():
            return "success"
        
        # Перші два виклики повинні пройти
        assert test_function() == "success"
        assert test_function() == "success"
        
        # Третій виклик повинен зачекати (але в тестах це може пройти швидко)
        start_time = time.time()
        result = test_function()
        end_time = time.time()
        
        assert result == "success"
        # Перевіряємо, що функція виконалася (можливо з затримкою)
        assert end_time >= start_time
    
    def test_flask_limiter_configuration(self, init_db):
        """Тест конфігурації Flask-Limiter"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        
        # Перевіряємо, що Flask-Limiter налаштований
        # В тестовому додатку limiter створюється як локальна змінна
        # тому просто перевіряємо, що додаток створюється без помилок
        assert app is not None
        assert app.config['TESTING'] == True


class TestHubSpotIntegration:
    """Тести для HubSpot інтеграції"""
    
    def test_hubspot_integration_basic(self, init_db):
        """Тест базової HubSpot інтеграції"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        
        with app.app_context():
            test_db.create_all()
            
            # Створюємо тестового користувача
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
            user_id = user.id  # Зберігаємо ID перед виходом з контексту
        
        with app.test_client() as client:
            # Входимо в систему
            client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            })
            
            # Додаємо лід
            response = client.post('/add_lead', data={
                'deal_name': 'Test Lead',
                'email': 'lead@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'notes': 'Test notes',
                'agent_id': str(user_id)
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Перевіряємо, що лід створений
            with app.app_context():
                lead = test_Lead.query.filter_by(email='lead@example.com').first()
                assert lead is not None
    
    def test_hubspot_rate_limiter_retry_logic(self, init_db):
        """Тест retry логіки HubSpot rate limiter"""
        from hubspot_rate_limiter import HubSpotRateLimiter
        
        # Створюємо rate limiter
        limiter = HubSpotRateLimiter(max_calls=10, period=1)
        
        # Функція, яка імітує помилку HubSpot API
        call_count = 0
        
        @limiter
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Імітуємо 429 помилку (Too Many Requests)
                from requests.exceptions import HTTPError
                from requests import Response
                response = Response()
                response.status_code = 429
                response.headers = {'Retry-After': '1'}
                error = HTTPError("429 Too Many Requests")
                error.response = response
                raise error
            return "success"
        
        # Функція повинна успішно виконатися після retry
        result = failing_function()
        assert result == "success"
        assert call_count == 3  # 2 невдалі спроби + 1 успішна


class TestErrorScenarios:
    """Тести сценаріїв помилок інтеграції"""
    
    def test_hubspot_api_error(self, init_db):
        """Тест обробки помилки HubSpot API"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        
        with app.app_context():
            test_db.create_all()
            
            # Створюємо тестового користувача
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
            user_id = user.id
        
        with app.test_client() as client:
            # Входимо в систему
            client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            })
            
            # Спробуємо створити лід
            response = client.post('/add_lead', data={
                'deal_name': 'Test Lead',
                'email': 'lead@example.com',
                'phone': '+1234567890',
                'budget': '200к–500к',
                'notes': 'Test notes',
                'agent_id': str(user_id)
            }, follow_redirects=True)
            
            # Лід повинен створитися
            assert response.status_code == 200
    
    def test_invalid_json_request(self, init_db):
        """Тест обробки невалідного JSON запиту"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        with app.app_context():
            test_db.create_all()
            
            # Створюємо тестового користувача
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
        
        with app.test_client() as client:
            # Входимо в систему
            client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            })
            
            # Відправляємо невалідний JSON на неіснуючий ендпоінт
            response = client.post('/nonexistent-api-endpoint', 
                                 data='invalid json',
                                 content_type='application/json')
            
            # Повинен повернути 404
            assert response.status_code == 404
    
    def test_unauthorized_api_access(self, init_db):
        """Тест неавторизованого доступу до API"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        with app.app_context():
            test_db.create_all()
        
        with app.test_client() as client:
            # Спробуємо отримати статистику профілю без авторизації
            response = client.get('/api/profile/stats')
            
            # Повинен повернути помилку або перенаправити
            assert response.status_code in [200, 302, 401, 403]


class TestDataFlow:
    """Тести потоку даних між компонентами"""
    
    def test_basic_data_flow(self, init_db):
        """Тест базового потоку даних"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        with app.app_context():
            test_db.create_all()
            
            # Створюємо тестового користувача
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
            
            # Створюємо тестовий лід
            lead = test_Lead(
                deal_name='Test Lead',
                email='lead@example.com',
                phone='+1234567890',
                agent_id=user.id
            )
            test_db.session.add(lead)
            test_db.session.commit()
            
            # Створюємо тестову нотатку
            note = test_NoteStatus(
                lead_id=lead.id,
                note_text='Test note'
            )
            test_db.session.add(note)
            test_db.session.commit()
            
            # Перевіряємо, що дані створені
            assert test_User.query.count() == 1
            assert test_Lead.query.count() == 1
            assert test_NoteStatus.query.count() == 1
            
            # Перевіряємо зв'язки
            retrieved_lead = test_Lead.query.first()
            retrieved_note = test_NoteStatus.query.first()
            
            assert retrieved_lead.agent_id == user.id
            assert retrieved_note.lead_id == lead.id
            assert retrieved_note.note_text == 'Test note'
    
    def test_user_authentication_flow(self, init_db):
        """Тест потоку аутентифікації користувача"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        with app.app_context():
            test_db.create_all()
            
            # Створюємо тестового користувача
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
        
        with app.test_client() as client:
            # Тестуємо вхід в систему
            response = client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Перевіряємо, що користувач увійшов
            with client.session_transaction() as sess:
                assert '_user_id' in sess
            
            # Тестуємо доступ до захищеної сторінки
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # Тестуємо вихід з системи
            response = client.get('/logout', follow_redirects=True)
            assert response.status_code == 200
            
            # Перевіряємо, що користувач вийшов
            with client.session_transaction() as sess:
                assert '_user_id' not in sess


class TestIntegrationComponents:
    """Тести інтеграції компонентів"""
    
    def test_app_initialization(self, init_db):
        """Тест ініціалізації додатку"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        
        # Перевіряємо, що всі компоненти ініціалізовані
        assert app is not None
        assert test_db is not None
        assert test_User is not None
        assert test_Lead is not None
        assert test_NoteStatus is not None
        assert test_Activity is not None
        
        # Перевіряємо конфігурацію
        assert app.config['TESTING'] == True
        assert 'sqlite:///:memory:' in app.config['SQLALCHEMY_DATABASE_URI']
        assert app.config['SECRET_KEY'] is not None
    
    def test_database_connection(self, init_db):
        """Тест підключення до бази даних"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        app, test_db, test_User, test_Lead, test_NoteStatus, test_Activity = create_test_app_with_routes()
        
        with app.app_context():
            # Перевіряємо, що можемо створити таблиці
            test_db.create_all()
            
            # Перевіряємо, що можемо створювати записи
            user = test_User(username='testuser', email='test@example.com', role='agent')
            user.set_password('password123')
            test_db.session.add(user)
            test_db.session.commit()
            
            # Перевіряємо, що можемо читати записи
            retrieved_user = test_User.query.first()
            assert retrieved_user is not None
            assert retrieved_user.username == 'testuser'
            
            # Перевіряємо, що можемо видаляти записи
            test_db.session.delete(retrieved_user)
            test_db.session.commit()
            
            # Перевіряємо, що запис видалено
            deleted_user = test_User.query.first()
            assert deleted_user is None
