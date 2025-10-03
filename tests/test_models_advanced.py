"""
Розширені тести для моделей ProPart Real Estate Hub
Включає edge cases, валідацію та складні сценарії
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import re

from app import db, User, Lead, NoteStatus, Activity


class TestUserModelAdvanced:
    """Розширені тести для моделі User"""
    
    def test_user_username_validation_edge_cases(self, init_db):
        """Тест валідації імені користувача - граничні випадки"""
        
        # Тест з мінімальною довжиною
        user = User(
            username='user',  # 4 символи - мінімум
            email='minimal@example.com',
            role='agent'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        saved_user = User.query.filter_by(username='user').first()
        assert saved_user is not None
        
        # Тест з максимальною довжиною
        long_username = 'a' * 25  # 25 символів - максимум
        user_long = User(
            username=long_username,
            email='long@example.com',
            role='agent'
        )
        user_long.set_password('password123')
        db.session.add(user_long)
        db.session.commit()
        
        saved_long_user = User.query.filter_by(username=long_username).first()
        assert saved_long_user is not None
    
    def test_user_email_validation(self, init_db):
        """Тест валідації email"""
        
        # Валідні email адреси
        valid_emails = [
            'user@example.com',
            'user.name@example.com',
            'user+tag@example.com',
            'user123@example-domain.co.uk'
        ]
        
        for i, email in enumerate(valid_emails):
            user = User(
                username=f'user{i}',
                email=email,
                role='agent'
            )
            user.set_password('password123')
            db.session.add(user)
        
        db.session.commit()
        
        # Перевіряємо, що всі користувачі створені
        for i, email in enumerate(valid_emails):
            user = User.query.filter_by(email=email).first()
            assert user is not None
    
    def test_user_role_validation(self, init_db):
        """Тест валідації ролей користувача"""
        
        # Тест валідних ролей
        valid_roles = ['agent', 'admin']
        
        for i, role in enumerate(valid_roles):
            user = User(
                username=f'user{i}',
                email=f'user{i}@example.com',
                role=role
            )
            user.set_password('password123')
            db.session.add(user)
        
        db.session.commit()
        
        # Перевіряємо, що користувачі з валідними ролями створені
        agent_user = User.query.filter_by(role='agent').first()
        admin_user = User.query.filter_by(role='admin').first()
        
        assert agent_user is not None
        assert admin_user is not None
    
    def test_user_points_edge_cases(self, init_db):
        """Тест граничних випадків для поінтів"""
        
        user = User(
            username='points_user',
            email='points@example.com',
            role='agent'
        )
        user.set_password('password123')
        
        # Тест з від'ємними поінтами (не повинно бути дозволено)
        user.points = -100
        user.update_level()
        assert user.level == 'bronze'  # Завжди бронза для від'ємних поінтів
        
        # Тест з нульовими поінтами
        user.points = 0
        user.update_level()
        assert user.level == 'bronze'
        
        # Тест з дуже великою кількістю поінтів
        user.points = 999999999
        user.update_level()
        assert user.level == 'platinum'  # Максимальний рівень
    
    def test_user_level_boundaries(self, init_db):
        """Тест границь рівнів користувача"""
        
        user = User(
            username='level_user',
            email='level@example.com',
            role='agent'
        )
        user.set_password('password123')
        
        # Тест точно на границі рівнів
        boundaries = [
            (1999, 'bronze'),    # 1 поінт менше срібла
            (2000, 'silver'),    # Точно на границі срібла
            (2001, 'silver'),    # 1 поінт більше срібла
            (4999, 'silver'),    # 1 поінт менше золота
            (5000, 'gold'),      # Точно на границі золота
            (5001, 'gold'),      # 1 поінт більше золота
            (9999, 'gold'),      # 1 поінт менше платини
            (10000, 'platinum'), # Точно на границі платини
            (10001, 'platinum')  # 1 поінт більше платини
        ]
        
        for points, expected_level in boundaries:
            user.points = points
            user.update_level()
            assert user.level == expected_level, f"Помилка для {points} поінтів: очікувався {expected_level}, отримано {user.level}"
    
    def test_user_account_locking_time_boundaries(self, init_db, frozen_time):
        """Тест границь часу блокування акаунту"""
        
        user = User(
            username='lock_user',
            email='lock@example.com',
            role='agent'
        )
        user.set_password('password123')
        
        # Блокуємо акаунт на 1 хвилину
        user.lock_account(1)
        assert user.is_account_locked() == True
        
        # Блокуємо акаунт на 0 хвилин (повинно розблокувати)
        user.lock_account(0)
        assert user.is_account_locked() == False
        
        # Блокуємо акаунт на дуже великий час
        user.lock_account(999999)  # Близько 694 днів
        assert user.is_account_locked() == True
    
    def test_user_login_attempts_boundaries(self, init_db):
        """Тест границь спроб входу"""
        
        user = User(
            username='attempts_user',
            email='attempts@example.com',
            role='agent'
        )
        user.set_password('password123')
        
        # Тест з 4 спробами (не повинно блокувати)
        for i in range(4):
            user.increment_login_attempts()
            assert user.login_attempts == i + 1
            assert user.is_account_locked() == False
        
        # 5-та спроба повинна заблокувати
        user.increment_login_attempts()
        assert user.login_attempts == 0  # Скидається при блокуванні
        assert user.is_account_locked() == True
    
    def test_user_verification_workflow(self, init_db):
        """Тест повного workflow верифікації"""
        
        user = User(
            username='verify_user',
            email='verify@example.com',
            role='agent'
        )
        user.set_password('password123')
        
        # Початковий стан
        assert user.is_verified == False
        assert user.verification_requested == False
        
        # Запит на верифікацію
        user.verification_requested = True
        user.verification_request_date = datetime.now()
        user.verification_document_path = '/path/to/document.pdf'
        user.verification_notes = 'Please verify this agent'
        
        assert user.verification_requested == True
        assert user.verification_request_date is not None
        assert user.verification_document_path is not None
        assert user.verification_notes is not None
        
        # Верифікація
        user.is_verified = True
        user.verification_requested = False
        
        assert user.is_verified == True
        assert user.verification_requested == False
        # Дата запиту та документи залишаються для історії
    
    def test_user_commission_calculation_edge_cases(self, init_db):
        """Тест розрахунку комісії для граничних випадків"""
        
        user = User(
            username='commission_user',
            email='commission@example.com',
            role='agent'
        )
        user.set_password('password123')
        
        # Тест з неіснуючим рівнем
        user.level = 'nonexistent'
        assert user.get_commission_rate() == 5  # За замовчуванням
        
        # Тест з None рівнем
        user.level = None
        assert user.get_commission_rate() == 5  # За замовчуванням
        
        # Тест з пустим рядком
        user.level = ''
        assert user.get_commission_rate() == 5  # За замовчуванням


class TestLeadModelAdvanced:
    """Розширені тести для моделі Lead"""
    
    def test_lead_email_validation_edge_cases(self, init_db, create_test_user):
        """Тест валідації email ліда - граничні випадки"""
        
        user = create_test_user
        
        # Валідні email адреси
        valid_emails = [
            'lead@example.com',
            'lead.name@example.com',
            'lead+tag@example.com',
            'lead123@example-domain.co.uk',
            'тест@example.com',  # Кирилиця в локальній частині
            'test@тест.com'      # Кирилиця в домені
        ]
        
        for i, email in enumerate(valid_emails):
            lead = Lead(
                agent_id=user.id,
                deal_name=f'Lead {i}',
                email=email,
                phone='+380501234567'
            )
            db.session.add(lead)
        
        db.session.commit()
        
        # Перевіряємо, що всі ліди створені
        for i, email in enumerate(valid_emails):
            lead = Lead.query.filter_by(email=email).first()
            assert lead is not None
    
    def test_lead_phone_validation(self, init_db, create_test_user):
        """Тест валідації телефонних номерів"""
        
        user = create_test_user
        
        # Валідні телефонні номери
        valid_phones = [
            '+380501234567',
            '+3805012345678',
            '+38050123456',
            '380501234567',
            '+1-555-123-4567',
            '+44 20 7946 0958',
            '+49 30 12345678'
        ]
        
        for i, phone in enumerate(valid_phones):
            lead = Lead(
                agent_id=user.id,
                deal_name=f'Phone Lead {i}',
                email=f'phone{i}@example.com',
                phone=phone
            )
            db.session.add(lead)
        
        db.session.commit()
        
        # Перевіряємо, що всі ліди створені
        for i, phone in enumerate(valid_phones):
            lead = Lead.query.filter_by(phone=phone).first()
            assert lead is not None
    
    def test_lead_budget_validation(self, init_db, create_test_user):
        """Тест валідації бюджетів"""
        
        user = create_test_user
        
        # Валідні бюджети
        valid_budgets = [
            'до 200к',
            '200к–500к',
            '500к–1млн',
            '1млн+',
            '',  # Пустий бюджет
            None  # Null бюджет
        ]
        
        for i, budget in enumerate(valid_budgets):
            lead = Lead(
                agent_id=user.id,
                deal_name=f'Budget Lead {i}',
                email=f'budget{i}@example.com',
                budget=budget
            )
            db.session.add(lead)
        
        db.session.commit()
        
        # Перевіряємо, що всі ліди створені
        for i in range(len(valid_budgets)):
            lead = Lead.query.filter_by(deal_name=f'Budget Lead {i}').first()
            assert lead is not None
    
    def test_lead_status_validation(self, init_db, create_test_user):
        """Тест валідації статусів ліда"""
        
        user = create_test_user
        
        # Валідні статуси
        valid_statuses = [
            'new',
            'contacted',
            'qualified',
            'closed',
            'custom_status',  # Кастомний статус
            ''  # Пустий статус
        ]
        
        for i, status in enumerate(valid_statuses):
            lead = Lead(
                agent_id=user.id,
                deal_name=f'Status Lead {i}',
                email=f'status{i}@example.com',
                status=status
            )
            db.session.add(lead)
        
        db.session.commit()
        
        # Перевіряємо, що всі ліди створені
        for i, status in enumerate(valid_statuses):
            lead = Lead.query.filter_by(deal_name=f'Status Lead {i}').first()
            assert lead is not None
            assert lead.status == status
    
    def test_lead_country_validation(self, init_db, create_test_user):
        """Тест валідації країн"""
        
        user = create_test_user
        
        # Валідні країни
        valid_countries = [
            'Дубай',
            'Турція',
            'Балі',
            'Таїланд',
            'Камбоджа',
            'Оман',
            'Абу-Дабі',
            'Мальдіви',
            'Румунія',
            'Іспанія',
            'Чорногорія',
            'Греція',
            'Північний Кіпр',
            'Південний Кіпр',
            '',  # Пуста країна
            None  # Null країна
        ]
        
        for i, country in enumerate(valid_countries):
            lead = Lead(
                agent_id=user.id,
                deal_name=f'Country Lead {i}',
                email=f'country{i}@example.com',
                country=country
            )
            db.session.add(lead)
        
        db.session.commit()
        
        # Перевіряємо, що всі ліди створені
        for i in range(len(valid_countries)):
            lead = Lead.query.filter_by(deal_name=f'Country Lead {i}').first()
            assert lead is not None
    
    def test_lead_hubspot_integration_fields(self, init_db, create_test_user):
        """Тест полів інтеграції з HubSpot"""
        
        user = create_test_user
        
        # Тест з HubSpot ID
        lead = Lead(
            agent_id=user.id,
            deal_name='HubSpot Lead',
            email='hubspot@example.com',
            hubspot_contact_id='hs_contact_123',
            hubspot_deal_id='hs_deal_456'
        )
        
        db.session.add(lead)
        db.session.commit()
        
        saved_lead = Lead.query.filter_by(email='hubspot@example.com').first()
        assert saved_lead is not None
        assert saved_lead.hubspot_contact_id == 'hs_contact_123'
        assert saved_lead.hubspot_deal_id == 'hs_deal_456'
        
        # Тест без HubSpot ID
        lead_no_hubspot = Lead(
            agent_id=user.id,
            deal_name='No HubSpot Lead',
            email='nohubspot@example.com'
        )
        
        db.session.add(lead_no_hubspot)
        db.session.commit()
        
        saved_lead_no_hubspot = Lead.query.filter_by(email='nohubspot@example.com').first()
        assert saved_lead_no_hubspot is not None
        assert saved_lead_no_hubspot.hubspot_contact_id is None
        assert saved_lead_no_hubspot.hubspot_deal_id is None
    
    def test_lead_transfer_status(self, init_db, create_test_user):
        """Тест статусу передачі ліда"""
        
        user = create_test_user
        
        # Лід не переданий
        lead_not_transferred = Lead(
            agent_id=user.id,
            deal_name='Not Transferred Lead',
            email='nottransferred@example.com'
        )
        assert lead_not_transferred.is_transferred == False
        
        # Лід переданий
        lead_transferred = Lead(
            agent_id=user.id,
            deal_name='Transferred Lead',
            email='transferred@example.com',
            is_transferred=True
        )
        assert lead_transferred.is_transferred == True
        
        db.session.add_all([lead_not_transferred, lead_transferred])
        db.session.commit()
        
        # Перевіряємо в базі даних
        not_transferred = Lead.query.filter_by(email='nottransferred@example.com').first()
        transferred = Lead.query.filter_by(email='transferred@example.com').first()
        
        assert not_transferred.is_transferred == False
        assert transferred.is_transferred == True


class TestNoteStatusModelAdvanced:
    """Розширені тести для моделі NoteStatus"""
    
    def test_note_text_validation(self, init_db, create_test_lead):
        """Тест валідації тексту нотатки"""
        
        lead = create_test_lead
        
        # Тест з різними типами тексту
        test_texts = [
            'Коротка нотатка',
            'Дуже довга нотатка ' + 'x' * 1000,  # 1000+ символів
            'Нотатка з кирилицею: тест',
            'Note with English text',
            'Нотатка з цифрами: 1234567890',
            'Нотатка з символами: !@#$%^&*()',
            '',  # Пуста нотатка
            '   ',  # Тільки пробіли
            '\n\n\n',  # Тільки переноси рядків
        ]
        
        for i, text in enumerate(test_texts):
            note = NoteStatus(
                lead_id=lead.id,
                note_text=text,
                status='sent'
            )
            db.session.add(note)
        
        db.session.commit()
        
        # Перевіряємо, що всі нотатки створені
        notes = NoteStatus.query.filter_by(lead_id=lead.id).all()
        assert len(notes) == len(test_texts)
    
    def test_note_status_workflow(self, init_db, create_test_lead):
        """Тест workflow статусів нотатки"""
        
        lead = create_test_lead
        
        # Створюємо нотатку зі статусом 'sent'
        note = NoteStatus(
            lead_id=lead.id,
            note_text='Test workflow note',
            status='sent'
        )
        
        db.session.add(note)
        db.session.commit()
        
        # Симулюємо workflow: sent -> read -> replied
        saved_note = NoteStatus.query.get(note.id)
        
        # Відправлено
        assert saved_note.status == 'sent'
        
        # Прочитано
        saved_note.status = 'read'
        db.session.commit()
        
        updated_note = NoteStatus.query.get(note.id)
        assert updated_note.status == 'read'
        
        # Відповідь отримана
        updated_note.status = 'replied'
        db.session.commit()
        
        final_note = NoteStatus.query.get(note.id)
        assert final_note.status == 'replied'
    
    def test_note_timestamps(self, init_db, create_test_lead, frozen_time):
        """Тест часових міток нотаток"""
        
        lead = create_test_lead
        
        # Створюємо нотатку
        note = NoteStatus(
            lead_id=lead.id,
            note_text='Timestamp test note',
            status='sent'
        )
        
        db.session.add(note)
        db.session.commit()
        
        saved_note = NoteStatus.query.get(note.id)
        
        # Перевіряємо, що часові мітки встановлені
        assert saved_note.created_at is not None
        assert saved_note.updated_at is not None
        
        # Перевіряємо, що created_at та updated_at однакові при створенні
        assert saved_note.created_at == saved_note.updated_at
        
        # Оновлюємо нотатку
        saved_note.status = 'read'
        db.session.commit()
        
        updated_note = NoteStatus.query.get(note.id)
        
        # Перевіряємо, що updated_at змінився
        assert updated_note.updated_at > updated_note.created_at


class TestActivityModelAdvanced:
    """Розширені тести для моделі Activity"""
    
    def test_activity_type_validation(self, init_db, create_test_lead):
        """Тест валідації типів активностей"""
        
        lead = create_test_lead
        
        # Валідні типи активностей
        valid_types = [
            'email',
            'call',
            'task',
            'meeting',
            'note',
            'custom_type'  # Кастомний тип
        ]
        
        for i, activity_type in enumerate(valid_types):
            activity = Activity(
                lead_id=lead.id,
                activity_type=activity_type,
                subject=f'Activity {i}'
            )
            db.session.add(activity)
        
        db.session.commit()
        
        # Перевіряємо, що всі активності створені
        activities = Activity.query.filter_by(lead_id=lead.id).all()
        assert len(activities) == len(valid_types)
        
        for i, activity_type in enumerate(valid_types):
            activity = Activity.query.filter_by(
                lead_id=lead.id,
                subject=f'Activity {i}'
            ).first()
            assert activity is not None
            assert activity.activity_type == activity_type
    
    def test_activity_direction_validation(self, init_db, create_test_lead):
        """Тест валідації напрямків активностей"""
        
        lead = create_test_lead
        
        # Валідні напрямки
        valid_directions = [
            'inbound',
            'outbound',
            '',  # Пустий напрямок
            None  # Null напрямок
        ]
        
        for i, direction in enumerate(valid_directions):
            activity = Activity(
                lead_id=lead.id,
                activity_type='email',
                subject=f'Direction Activity {i}',
                direction=direction
            )
            db.session.add(activity)
        
        db.session.commit()
        
        # Перевіряємо, що всі активності створені
        activities = Activity.query.filter_by(lead_id=lead.id).all()
        assert len(activities) == len(valid_directions)
    
    def test_activity_duration_validation(self, init_db, create_test_lead):
        """Тест валідації тривалості активностей"""
        
        lead = create_test_lead
        
        # Тест з різними тривалостями
        durations = [
            0,      # 0 секунд
            60,     # 1 хвилина
            3600,   # 1 година
            86400,  # 1 день
            0.5,    # 0.5 секунди (float)
            None    # Без тривалості
        ]
        
        for i, duration in enumerate(durations):
            activity = Activity(
                lead_id=lead.id,
                activity_type='call',
                subject=f'Duration Activity {i}',
                duration=duration
            )
            db.session.add(activity)
        
        db.session.commit()
        
        # Перевіряємо, що всі активності створені
        activities = Activity.query.filter_by(lead_id=lead.id).all()
        assert len(activities) == len(durations)
    
    def test_activity_hubspot_integration(self, init_db, create_test_lead):
        """Тест інтеграції активностей з HubSpot"""
        
        lead = create_test_lead
        
        # Активність з HubSpot ID
        activity_with_hubspot = Activity(
            lead_id=lead.id,
            activity_type='email',
            subject='HubSpot Email',
            hubspot_activity_id='hs_activity_123'
        )
        
        # Активність без HubSpot ID
        activity_without_hubspot = Activity(
            lead_id=lead.id,
            activity_type='call',
            subject='Local Call'
        )
        
        db.session.add_all([activity_with_hubspot, activity_without_hubspot])
        db.session.commit()
        
        # Перевіряємо HubSpot інтеграцію
        hubspot_activity = Activity.query.filter_by(
            hubspot_activity_id='hs_activity_123'
        ).first()
        assert hubspot_activity is not None
        
        local_activity = Activity.query.filter_by(
            subject='Local Call'
        ).first()
        assert local_activity is not None
        assert local_activity.hubspot_activity_id is None
    
    def test_activity_status_workflow(self, init_db, create_test_lead):
        """Тест workflow статусів активностей"""
        
        lead = create_test_lead
        
        # Створюємо активність зі статусом 'completed'
        activity = Activity(
            lead_id=lead.id,
            activity_type='task',
            subject='Test task',
            status='completed'
        )
        
        db.session.add(activity)
        db.session.commit()
        
        saved_activity = Activity.query.get(activity.id)
        
        # Завершена
        assert saved_activity.status == 'completed'
        
        # В процесі
        saved_activity.status = 'pending'
        db.session.commit()
        
        updated_activity = Activity.query.get(activity.id)
        assert updated_activity.status == 'pending'
        
        # Скасована
        updated_activity.status = 'cancelled'
        db.session.commit()
        
        final_activity = Activity.query.get(activity.id)
        assert final_activity.status == 'cancelled'


class TestModelConstraints:
    """Тести обмежень моделей"""
    
    def test_user_unique_constraints(self, init_db):
        """Тест унікальних обмежень користувача"""
        
        # Створюємо першого користувача
        user1 = User(
            username='unique_user',
            email='unique@example.com',
            role='agent'
        )
        user1.set_password('password123')
        
        db.session.add(user1)
        db.session.commit()
        
        # Спробуємо створити користувача з дублікатом username
        user2 = User(
            username='unique_user',  # Дублікат
            email='unique2@example.com',
            role='agent'
        )
        user2.set_password('password123')
        
        db.session.add(user2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
        
        db.session.rollback()
        
        # Спробуємо створити користувача з дублікатом email
        user3 = User(
            username='unique_user3',
            email='unique@example.com',  # Дублікат
            role='agent'
        )
        user3.set_password('password123')
        
        db.session.add(user3)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
    
    def test_lead_foreign_key_constraint(self, init_db):
        """Тест обмеження зовнішнього ключа ліда"""
        
        # Спробуємо створити лід з неіснуючим agent_id
        lead = Lead(
            agent_id=99999,  # Неіснуючий ID
            deal_name='Invalid Lead',
            email='invalid@example.com'
        )
        
        db.session.add(lead)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
    
    def test_note_foreign_key_constraint(self, init_db):
        """Тест обмеження зовнішнього ключа нотатки"""
        
        # Спробуємо створити нотатку з неіснуючим lead_id
        note = NoteStatus(
            lead_id=99999,  # Неіснуючий ID
            note_text='Invalid note',
            status='sent'
        )
        
        db.session.add(note)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
    
    def test_activity_foreign_key_constraint(self, init_db):
        """Тест обмеження зовнішнього ключа активності"""
        
        # Спробуємо створити активність з неіснуючим lead_id
        activity = Activity(
            lead_id=99999,  # Неіснуючий ID
            activity_type='email',
            subject='Invalid activity'
        )
        
        db.session.add(activity)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
    
    def test_activity_hubspot_unique_constraint(self, init_db, create_test_lead):
        """Тест унікального обмеження HubSpot ID активності"""
        
        lead = create_test_lead
        
        # Створюємо першу активність з HubSpot ID
        activity1 = Activity(
            lead_id=lead.id,
            activity_type='email',
            subject='First email',
            hubspot_activity_id='hs_activity_123'
        )
        
        db.session.add(activity1)
        db.session.commit()
        
        # Спробуємо створити другу активність з тим же HubSpot ID
        activity2 = Activity(
            lead_id=lead.id,
            activity_type='call',
            subject='Second call',
            hubspot_activity_id='hs_activity_123'  # Дублікат
        )
        
        db.session.add(activity2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
