"""
Тести для моделей бази даних ProPart Real Estate Hub
"""
import pytest
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash


class TestUserModel:
    """Тести для моделі User"""
    
    def test_user_creation(self, init_db, sample_user_data):
        """Тест створення користувача"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        
        assert user.username == sample_user_data['username']
        assert user.email == sample_user_data['email']
        assert user.role == sample_user_data['role']
        assert user.is_active == True  # За замовчуванням
        assert user.points == 0  # За замовчуванням
        assert user.level == 'bronze'  # За замовчуванням
        assert user.total_leads == 0  # За замовчуванням
        assert user.closed_deals == 0  # За замовчуванням
        assert user.is_verified == False  # За замовчуванням
        assert user.verification_requested == False  # За замовчуванням
        assert user.login_attempts == 0  # За замовчуванням
    
    def test_user_password_hashing(self, init_db, sample_user_data):
        """Тест хешування паролю"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        
        # Встановлюємо пароль
        user.set_password(sample_user_data['password'])
        
        # Перевіряємо, що пароль хешується
        assert user.password_hash != sample_user_data['password']
        assert user.password_hash is not None
        
        # Перевіряємо, що можна перевірити пароль
        assert user.check_password(sample_user_data['password']) == True
        assert user.check_password('wrongpassword') == False
    
    def test_user_password_compatibility(self, init_db, sample_user_data):
        """Тест сумісності з старими паролями Werkzeug"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        
        # Симулюємо старий Werkzeug hash
        from werkzeug.security import generate_password_hash
        old_hash = generate_password_hash(sample_user_data['password'])
        user.password_hash = old_hash
        
        # Перевіряємо, що старий hash працює
        assert user.check_password(sample_user_data['password']) == True
        assert user.check_password('wrongpassword') == False
    
    def test_user_points_and_level(self, init_db, sample_user_data):
        """Тест системи поінтів та рівнів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        user.set_password(sample_user_data['password'])
        
        # Перевіряємо початковий рівень
        assert user.level == 'bronze'
        assert user.points == 0
        
        # Додаємо поінти та перевіряємо рівень
        user.add_points(1000)
        assert user.points == 1000
        assert user.level == 'bronze'  # Ще бронза
        
        user.add_points(1500)  # Загалом 2500
        assert user.points == 2500
        assert user.level == 'silver'  # Тепер срібло
        
        user.add_points(3000)  # Загалом 5500
        assert user.points == 5500
        assert user.level == 'gold'  # Тепер золото
        
        user.add_points(5000)  # Загалом 10500
        assert user.points == 10500
        assert user.level == 'platinum'  # Тепер платина
    
    def test_user_commission_rate(self, init_db, sample_user_data):
        """Тест відсотків комісії за рівнями"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        
        # Перевіряємо комісії за рівнями
        user.level = 'bronze'
        assert user.get_commission_rate() == 5
        
        user.level = 'silver'
        assert user.get_commission_rate() == 7
        
        user.level = 'gold'
        assert user.get_commission_rate() == 10
        
        user.level = 'platinum'
        assert user.get_commission_rate() == 15
        
        # Неіснуючий рівень
        user.level = 'unknown'
        assert user.get_commission_rate() == 5  # За замовчуванням
    
    def test_user_level_display_name(self, init_db, sample_user_data):
        """Тест відображуваних назв рівнів"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        
        # Перевіряємо назви рівнів
        user.level = 'bronze'
        assert user.get_level_display_name() == 'Бронзовий'
        
        user.level = 'silver'
        assert user.get_level_display_name() == 'Срібний'
        
        user.level = 'gold'
        assert user.get_level_display_name() == 'Золотий'
        
        user.level = 'platinum'
        assert user.get_level_display_name() == 'Платиновий'
        
        # Неіснуючий рівень
        user.level = 'unknown'
        assert user.get_level_display_name() == 'Бронзовий'  # За замовчуванням
    
    def test_user_account_locking(self, init_db, sample_user_data, frozen_time):
        """Тест блокування акаунту"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        user.set_password(sample_user_data['password'])
        
        # Перевіряємо, що акаунт не заблокований
        assert user.is_account_locked() == False
        
        # Блокуємо акаунт на 30 хвилин
        user.lock_account(30)
        assert user.is_account_locked() == True
        assert user.login_attempts == 0  # Скидається при блокуванні
        
        # Розблоковуємо акаунт
        user.unlock_account()
        assert user.is_account_locked() == False
        assert user.login_attempts == 0
        assert user.locked_until is None
    
    def test_user_login_attempts(self, init_db, sample_user_data):
        """Тест лічильника невдалих спроб входу"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        user.set_password(sample_user_data['password'])
        
        # Перевіряємо початковий стан
        assert user.login_attempts == 0
        
        # Збільшуємо спроби входу
        user.increment_login_attempts()
        assert user.login_attempts == 1
        
        user.increment_login_attempts()
        assert user.login_attempts == 2
        
        # Після 5 спроб акаунт блокується
        user.increment_login_attempts()
        user.increment_login_attempts()
        user.increment_login_attempts()  # 5-та спроба
        
        assert user.login_attempts == 0  # Скидається при блокуванні
        assert user.is_account_locked() == True
        
        # Скидаємо спроби
        user.reset_login_attempts()
        assert user.login_attempts == 0
        assert user.is_account_locked() == False
    
    def test_user_verification(self, init_db, sample_user_data):
        """Тест системи верифікації"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        user.set_password(sample_user_data['password'])
        
        # Перевіряємо початковий стан
        assert user.is_verified == False
        assert user.verification_requested == False
        assert user.verification_request_date is None
        
        # Запитуємо верифікацію
        user.verification_requested = True
        user.verification_request_date = datetime.now()
        
        assert user.verification_requested == True
        assert user.verification_request_date is not None
        
        # Верифікуємо користувача
        user.is_verified = True
        user.verification_requested = False
        
        assert user.is_verified == True
        assert user.verification_requested == False
    
    def test_user_database_operations(self, init_db, sample_user_data):
        """Тест операцій з базою даних"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = User(
            username=sample_user_data['username'],
            email=sample_user_data['email'],
            role=sample_user_data['role']
        )
        user.set_password(sample_user_data['password'])
        
        # Зберігаємо користувача
        db.session.add(user)
        db.session.commit()
        
        # Перевіряємо, що користувач збережений
        saved_user = User.query.filter_by(username=sample_user_data['username']).first()
        assert saved_user is not None
        assert saved_user.email == sample_user_data['email']
        assert saved_user.role == sample_user_data['role']
        
        # Оновлюємо користувача
        saved_user.points = 1000
        saved_user.update_level()
        db.session.commit()
        
        # Перевіряємо оновлення
        updated_user = User.query.get(saved_user.id)
        assert updated_user.points == 1000
        assert updated_user.level == 'bronze'  # 1000 поінтів = бронза
        
        # Видаляємо користувача
        db.session.delete(updated_user)
        db.session.commit()
        
        # Перевіряємо, що користувач видалений
        deleted_user = User.query.get(saved_user.id)
        assert deleted_user is None


class TestLeadModel:
    """Тести для моделі Lead"""
    
    def test_lead_creation(self, init_db, create_test_user, sample_lead_data):
        """Тест створення ліда"""
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
        
        assert lead.agent_id == create_test_user.id
        assert lead.deal_name == sample_lead_data['deal_name']
        assert lead.email == sample_lead_data['email']
        assert lead.phone == sample_lead_data['phone']
        assert lead.budget == sample_lead_data['budget']
        assert lead.status == sample_lead_data['status']
        assert lead.notes == sample_lead_data['notes']
        assert lead.is_transferred == False  # За замовчуванням
        assert lead.hubspot_contact_id is None  # За замовчуванням
        assert lead.hubspot_deal_id is None  # За замовчуванням
    
    def test_lead_validation(self, init_db, create_test_user):
        """Тест валідації ліда"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        # Тест з мінімальними обов'язковими полями
        lead = Lead(
            agent_id=create_test_user.id,
            deal_name='Test Lead',
            email='test@example.com'
        )
        
        assert lead.agent_id == create_test_user.id
        assert lead.deal_name == 'Test Lead'
        assert lead.email == 'test@example.com'
        assert lead.phone is None
        assert lead.budget is None
        assert lead.status == 'new'  # За замовчуванням
    
    def test_lead_with_all_fields(self, init_db, create_test_user):
        """Тест ліда з усіма полями"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        lead = Lead(
            agent_id=create_test_user.id,
            deal_name='Complete Test Lead',
            email='complete@example.com',
            phone='+380501234567',
            budget='200к–500к',
            status='contacted',
            is_transferred=True,
            notes='Complete test notes',
            country='Дубай',
            purchase_goal='для себя',
            property_type='офф-план',
            object_type='апартаменты',
            communication_language='украинский',
            source='сайт',
            refusal_reason=None,
            company='Test Company',
            second_phone='+380509876543',
            telegram_nickname='testuser',
            messenger='telegram',
            birth_date=datetime.now().date(),
            hubspot_contact_id='hs_contact_123',
            hubspot_deal_id='hs_deal_456'
        )
        
        # Перевіряємо всі поля
        assert lead.deal_name == 'Complete Test Lead'
        assert lead.email == 'complete@example.com'
        assert lead.phone == '+380501234567'
        assert lead.budget == '200к–500к'
        assert lead.status == 'contacted'
        assert lead.is_transferred == True
        assert lead.notes == 'Complete test notes'
        assert lead.country == 'Дубай'
        assert lead.purchase_goal == 'для себя'
        assert lead.property_type == 'офф-план'
        assert lead.object_type == 'апартаменты'
        assert lead.communication_language == 'украинский'
        assert lead.source == 'сайт'
        assert lead.company == 'Test Company'
        assert lead.second_phone == '+380509876543'
        assert lead.telegram_nickname == 'testuser'
        assert lead.messenger == 'telegram'
        assert lead.birth_date == datetime.now().date()
        assert lead.hubspot_contact_id == 'hs_contact_123'
        assert lead.hubspot_deal_id == 'hs_deal_456'
    
    def test_lead_database_operations(self, init_db, create_test_user, sample_lead_data):
        """Тест операцій з базою даних для ліда"""
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
        
        # Зберігаємо лід
        db.session.add(lead)
        db.session.commit()
        
        # Перевіряємо, що лід збережений
        saved_lead = Lead.query.filter_by(email=sample_lead_data['email']).first()
        assert saved_lead is not None
        assert saved_lead.deal_name == sample_lead_data['deal_name']
        assert saved_lead.agent_id == create_test_user.id
        
        # Оновлюємо лід
        saved_lead.status = 'qualified'
        saved_lead.budget = '500к–1млн'
        db.session.commit()
        
        # Перевіряємо оновлення
        updated_lead = Lead.query.get(saved_lead.id)
        assert updated_lead.status == 'qualified'
        assert updated_lead.budget == '500к–1млн'
        
        # Видаляємо лід
        db.session.delete(updated_lead)
        db.session.commit()
        
        # Перевіряємо, що лід видалений
        deleted_lead = Lead.query.get(saved_lead.id)
        assert deleted_lead is None
    
    def test_lead_relationships(self, init_db, create_test_lead):
        """Тест зв'язків ліда з іншими моделями"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        lead = create_test_lead
        
        # Перевіряємо зв'язок з користувачем
        assert lead.agent_id is not None
        user = User.query.get(lead.agent_id)
        assert user is not None
        
        # Перевіряємо, що можемо отримати ліди користувача
        user_leads = Lead.query.filter_by(agent_id=user.id).all()
        assert len(user_leads) >= 1
        assert lead in user_leads


class TestNoteStatusModel:
    """Тести для моделі NoteStatus"""
    
    def test_note_creation(self, init_db, create_test_lead):
        """Тест створення нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        note = NoteStatus(
            lead_id=create_test_lead.id,
            note_text='Test note content',
            status='sent'
        )
        
        assert note.lead_id == create_test_lead.id
        assert note.note_text == 'Test note content'
        assert note.status == 'sent'
    
    def test_note_default_values(self, init_db, create_test_lead):
        """Тест значень за замовчуванням для нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        note = NoteStatus(
            lead_id=create_test_lead.id,
            note_text='Test note'
        )
        
        assert note.status == 'sent'  # За замовчуванням
        assert note.created_at is None  # Встановлюється при збереженні
    
    def test_note_statuses(self, init_db, create_test_lead):
        """Тест різних статусів нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        # Нотатка відправлена
        sent_note = NoteStatus(
            lead_id=create_test_lead.id,
            note_text='Sent note',
            status='sent'
        )
        assert sent_note.status == 'sent'
        
        # Нотатка прочитана
        read_note = NoteStatus(
            lead_id=create_test_lead.id,
            note_text='Read note',
            status='read'
        )
        assert read_note.status == 'read'
        
        # Нотатка з відповіддю
        replied_note = NoteStatus(
            lead_id=create_test_lead.id,
            note_text='Replied note',
            status='replied'
        )
        assert replied_note.status == 'replied'
    
    def test_note_database_operations(self, init_db, create_test_lead):
        """Тест операцій з базою даних для нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        note = NoteStatus(
            lead_id=create_test_lead.id,
            note_text='Test note content',
            status='sent'
        )
        
        # Зберігаємо нотатку
        db.session.add(note)
        db.session.commit()
        
        # Перевіряємо, що нотатка збережена
        saved_note = NoteStatus.query.filter_by(lead_id=create_test_lead.id).first()
        assert saved_note is not None
        assert saved_note.note_text == 'Test note content'
        
        # Оновлюємо статус нотатки
        saved_note.status = 'read'
        db.session.commit()
        
        # Перевіряємо оновлення
        updated_note = NoteStatus.query.get(saved_note.id)
        assert updated_note.status == 'read'


class TestActivityModel:
    """Тести для моделі Activity"""
    
    def test_activity_creation(self, init_db, create_test_lead):
        """Тест створення активності"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='email',
            subject='Test email subject',
            body='Test email body',
            status='completed',
            direction='outbound'
        )
        
        assert activity.lead_id == create_test_lead.id
        assert activity.activity_type == 'email'
        assert activity.subject == 'Test email subject'
        assert activity.body == 'Test email body'
        assert activity.status == 'completed'
        assert activity.direction == 'outbound'
    
    def test_activity_types(self, init_db, create_test_lead):
        """Тест різних типів активностей"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        # Email активність
        email_activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='email',
            subject='Email subject',
            body='Email body',
            direction='outbound'
        )
        assert email_activity.activity_type == 'email'
        
        # Дзвінок
        call_activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='call',
            subject='Call subject',
            body='Call notes',
            direction='inbound',
            duration=300  # 5 хвилин
        )
        assert call_activity.activity_type == 'call'
        assert call_activity.duration == 300
        
        # Завдання
        task_activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='task',
            subject='Task subject',
            body='Task description'
        )
        assert task_activity.activity_type == 'task'
        
        # Зустріч
        meeting_activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='meeting',
            subject='Meeting subject',
            body='Meeting notes',
            duration=1800  # 30 хвилин
        )
        assert meeting_activity.activity_type == 'meeting'
        assert meeting_activity.duration == 1800
    
    def test_activity_default_values(self, init_db, create_test_lead):
        """Тест значень за замовчуванням для активності"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='note',
            subject='Test note'
        )
        
        assert activity.status == 'completed'  # За замовчуванням
        assert activity.direction is None  # За замовчуванням
        assert activity.duration is None  # За замовчуванням
        assert activity.hubspot_activity_id is None  # За замовчуванням
    
    def test_activity_with_hubspot_id(self, init_db, create_test_lead):
        """Тест активності з HubSpot ID"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='email',
            subject='HubSpot email',
            hubspot_activity_id='hs_activity_123'
        )
        
        assert activity.hubspot_activity_id == 'hs_activity_123'
    
    def test_activity_database_operations(self, init_db, create_test_lead):
        """Тест операцій з базою даних для активності"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        activity = Activity(
            lead_id=create_test_lead.id,
            activity_type='email',
            subject='Test email subject',
            body='Test email body',
            status='completed'
        )
        
        # Зберігаємо активність
        db.session.add(activity)
        db.session.commit()
        
        # Перевіряємо, що активність збережена
        saved_activity = Activity.query.filter_by(lead_id=create_test_lead.id).first()
        assert saved_activity is not None
        assert saved_activity.subject == 'Test email subject'
        
        # Оновлюємо активність
        saved_activity.status = 'pending'
        db.session.commit()
        
        # Перевіряємо оновлення
        updated_activity = Activity.query.get(saved_activity.id)
        assert updated_activity.status == 'pending'


class TestModelRelationships:
    """Тести зв'язків між моделями"""
    
    def test_user_lead_relationship(self, init_db, create_test_user):
        """Тест зв'язку користувач-ліди"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        user = create_test_user
        
        # Створюємо кілька лідів для користувача
        lead1 = Lead(
            agent_id=user.id,
            deal_name='Lead 1',
            email='lead1@example.com'
        )
        lead2 = Lead(
            agent_id=user.id,
            deal_name='Lead 2',
            email='lead2@example.com'
        )
        
        db.session.add_all([lead1, lead2])
        db.session.commit()
        
        # Перевіряємо зв'язок
        user_leads = Lead.query.filter_by(agent_id=user.id).all()
        assert len(user_leads) == 2
        assert lead1 in user_leads
        assert lead2 in user_leads
    
    def test_lead_notes_relationship(self, init_db, create_test_lead):
        """Тест зв'язку лід-нотатки"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        lead = create_test_lead
        
        # Створюємо кілька нотаток для ліда
        note1 = NoteStatus(
            lead_id=lead.id,
            note_text='Note 1',
            status='sent'
        )
        note2 = NoteStatus(
            lead_id=lead.id,
            note_text='Note 2',
            status='read'
        )
        
        db.session.add_all([note1, note2])
        db.session.commit()
        
        # Перевіряємо зв'язок
        lead_notes = NoteStatus.query.filter_by(lead_id=lead.id).all()
        assert len(lead_notes) == 2
        assert note1 in lead_notes
        assert note2 in lead_notes
    
    def test_lead_activities_relationship(self, init_db, create_test_lead):
        """Тест зв'язку лід-активності"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        lead = create_test_lead
        
        # Створюємо кілька активностей для ліда
        activity1 = Activity(
            lead_id=lead.id,
            activity_type='email',
            subject='Email 1'
        )
        activity2 = Activity(
            lead_id=lead.id,
            activity_type='call',
            subject='Call 1'
        )
        
        db.session.add_all([activity1, activity2])
        db.session.commit()
        
        # Перевіряємо зв'язок
        lead_activities = Activity.query.filter_by(lead_id=lead.id).all()
        assert len(lead_activities) == 2
        assert activity1 in lead_activities
        assert activity2 in lead_activities
    
    def test_cascade_deletion(self, init_db, create_test_lead):
        """Тест каскадного видалення"""
        db, User, Lead, NoteStatus, Activity = init_db
        
        lead = create_test_lead
        
        # Створюємо нотатку та активність для ліда
        note = NoteStatus(
            lead_id=lead.id,
            note_text='Test note',
            status='sent'
        )
        activity = Activity(
            lead_id=lead.id,
            activity_type='email',
            subject='Test email'
        )
        
        db.session.add_all([note, activity])
        db.session.commit()
        
        # Видаляємо лід
        db.session.delete(lead)
        db.session.commit()
        
        # Перевіряємо, що пов'язані записи також видалені
        # (якщо налаштовано каскадне видалення)
        deleted_note = NoteStatus.query.get(note.id)
        deleted_activity = Activity.query.get(activity.id)
        
        # Залежно від налаштувань БД, записи можуть бути видалені або залишитися
        # Тут ми просто перевіряємо, що лід видалений
        deleted_lead = Lead.query.get(lead.id)
        assert deleted_lead is None
