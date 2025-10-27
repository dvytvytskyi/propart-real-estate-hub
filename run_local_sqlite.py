#!/usr/bin/env python3
"""
Локальний запуск з SQLite для тестування
"""
import os
import pathlib

# КРИТИЧНО: Встановлюємо перед імпортом app
basedir = pathlib.Path(__file__).parent.absolute()
os.environ['DATABASE_URL'] = f'sqlite:///{basedir}/instance/propart.db'
os.environ['SECRET_KEY'] = 'dev-secret-key-for-local-testing'

print(f"🔄 Використовуємо SQLite: {os.environ['DATABASE_URL']}")

from app import app, db, User

def check_and_create_admin():
    """Перевірка та створення тестового адміна"""
    with app.app_context():
        print("🗄️ База даних:", app.config['SQLALCHEMY_DATABASE_URI'])
        
        # Створюємо таблиці якщо їх немає
        db.create_all()
        print("✅ Таблиці створено/перевірено")
        
        # Перевіряємо адмінів
        admins = User.query.filter_by(role='admin').all()
        print(f"\n👥 Знайдено адмінів: {len(admins)}")
        
        for admin in admins:
            print(f"  ✅ {admin.username} - {admin.email} (ID: {admin.id})")
        
        # Створюємо тестового адміна якщо немає
        if len(admins) == 0:
            print("\n⚠️ Створюємо тестового адміна...")
            test_admin = User(
                username='admin',
                email='admin@test.com',
                role='admin'
            )
            test_admin.set_password('admin123')
            db.session.add(test_admin)
            db.session.commit()
            print(f"✅ Тестовий адмін створено: admin / admin123")
        
        print("\n" + "=" * 70)
        print("🚀 Сервер запускається на http://localhost:5001")
        print("=" * 70)
        print("📝 ДЛЯ ТЕСТУВАННЯ РЕЄСТРАЦІЇ:")
        print("   1. Відкрийте http://localhost:5001/register у браузері")
        print("   2. Натисніть F12 щоб відкрити Developer Console")
        print("   3. Перейдіть на вкладку Console")
        print("   4. Заповніть форму реєстрації:")
        print("      - Ім'я користувача: test_user")
        print("      - Email: test@example.com")
        print("      - Виберіть адміна зі списку")
        print("      - Пароль та підтвердження")
        print("   5. Натисніть 'Зареєструватися'")
        print("   6. Дивіться логи:")
        print("      - В браузерній консолі (F12 -> Console)")
        print("      - В цій консолі (серверні логи)")
        print("=" * 70)
        print()

if __name__ == '__main__':
    check_and_create_admin()
    app.run(debug=True, host='0.0.0.0', port=5001)

