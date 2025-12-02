#!/usr/bin/env python3
"""
Скрипт для виправлення None значень у полях агентів
"""
from app import app, db, User

def fix_none_values():
    """Виправляє None значення для всіх агентів"""
    with app.app_context():
        users = User.query.all()
        fixed_count = 0
        
        for user in users:
            updated = False
            
            # Виправляємо points
            if user.points is None:
                user.points = 0
                updated = True
                print(f"✅ Виправлено points для {user.username}: None -> 0")
            
            # Виправляємо total_leads
            if user.total_leads is None:
                user.total_leads = 0
                updated = True
                print(f"✅ Виправлено total_leads для {user.username}: None -> 0")
            
            # Виправляємо closed_deals
            if user.closed_deals is None:
                user.closed_deals = 0
                updated = True
                print(f"✅ Виправлено closed_deals для {user.username}: None -> 0")
            
            # Виправляємо level
            if user.level is None:
                user.level = 'bronze'
                updated = True
                print(f"✅ Виправлено level для {user.username}: None -> bronze")
            
            if updated:
                fixed_count += 1
                # Оновлюємо рівень на основі поінтів
                user.update_level()
        
        if fixed_count > 0:
            db.session.commit()
            print(f"\n✅ Виправлено {fixed_count} користувачів")
        else:
            print("\n✅ Всі значення вже правильні")

if __name__ == '__main__':
    fix_none_values()

