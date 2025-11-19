#!/usr/bin/env python3
"""
Симуляція логіну агента через Flask test client
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def test_login_simulation(username, password):
    """Симулює логін через Flask test client"""
    with app.app_context():
        print("=" * 80)
        print(f"🧪 СИМУЛЯЦІЯ ЛОГІНУ: {username}")
        print("=" * 80)
        
        # Перевіряємо користувача
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"❌ Користувача '{username}' не знайдено")
            return False
        
        print(f"\n📊 Користувач знайдено:")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Role: {user.role}")
        print(f"   is_active: {user.is_active}")
        print(f"   is_account_locked(): {user.is_account_locked()}")
        
        # Перевіряємо пароль
        if not user.check_password(password):
            print(f"❌ Пароль неправильний!")
            return False
        
        print(f"✅ Пароль правильний")
        
        # Симулюємо логін через test client
        with app.test_client() as client:
            print(f"\n🌐 Симуляція HTTP запиту...")
            
            # GET /login
            response = client.get('/login')
            print(f"   GET /login: {response.status_code}")
            
            # POST /login
            response = client.post('/login', data={
                'username': username,
                'password': password
            }, follow_redirects=False)
            
            print(f"   POST /login: {response.status_code}")
            print(f"   Location header: {response.headers.get('Location', 'Немає')}")
            
            if response.status_code == 302:
                # Перевіряємо сесію
                with client.session_transaction() as sess:
                    user_id = sess.get('_user_id')
                    print(f"\n📝 СЕСІЯ:")
                    print(f"   _user_id в сесії: {user_id}")
                    print(f"   Тип: {type(user_id)}")
                    
                    if user_id:
                        print(f"   ✅ Сесія створена!")
                        
                        # Перевіряємо, чи можна завантажити користувача
                        from app import login_manager
                        loaded_user = login_manager.user_loader(str(user_id))
                        if loaded_user:
                            print(f"   ✅ user_loader завантажив користувача: {loaded_user.username}")
                        else:
                            print(f"   ❌ user_loader не завантажив користувача")
                    else:
                        print(f"   ❌ Сесія не створена!")
                        return False
                
                # Перевіряємо redirect
                if '/dashboard' in response.headers.get('Location', ''):
                    print(f"\n✅ Успішний redirect на /dashboard")
                    
                    # Спробуємо отримати dashboard
                    response = client.get('/dashboard', follow_redirects=True)
                    print(f"   GET /dashboard: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"   ✅ Dashboard завантажено успішно!")
                        return True
                    else:
                        print(f"   ❌ Dashboard не завантажено (статус: {response.status_code})")
                        return False
                else:
                    print(f"   ⚠️  Redirect не на /dashboard")
                    return False
            else:
                print(f"   ❌ Логін не вдався (статус: {response.status_code})")
                print(f"   Response data: {response.data[:500]}")
                return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        username = 'agent'
        password = 'agent123'
    
    if not password:
        known_passwords = {
            'agent': 'agent123',
            'olena_birovchak': 'temp_olena_birovchak123!',
            'ustyan': 'temp_ustyan123!',
        }
        password = known_passwords.get(username, '')
    
    if password:
        test_login_simulation(username, password)
    else:
        print(f"❌ Пароль не вказано для {username}")

