#!/usr/bin/env python3
"""
Призначення агентів до адмінів
- hatamatata, yanina_d, o_antipenko, ideal_home, gorzhiy, l_bogdanenko → alex_admin
- Всі інші агенти → anton_admin
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def assign_agents_to_admins():
    """Призначає агентів до адмінів"""
    
    # Агенти для alex_admin
    alex_agents = [
        'hatamatata',
        'yanina_d',
        'o_antipenko',
        'ideal_home',
        'gorzhiy',
        'l_bogdanenko'
    ]
    
    with app.app_context():
        print("=" * 80)
        print("🔧 ПРИЗНАЧЕННЯ АГЕНТІВ ДО АДМІНІВ")
        print("=" * 80)
        print()
        
        # Знаходимо адмінів
        alex_admin = User.query.filter_by(username='alex_admin', role='admin').first()
        anton_admin = User.query.filter_by(username='anton_admin', role='admin').first()
        
        if not alex_admin:
            print("❌ Адмін alex_admin не знайдено!")
            return False
        
        if not anton_admin:
            print("❌ Адмін anton_admin не знайдено!")
            return False
        
        print(f"✅ Знайдено адмінів:")
        print(f"   - alex_admin (ID: {alex_admin.id})")
        print(f"   - anton_admin (ID: {anton_admin.id})")
        print()
        
        # Призначаємо агентів для alex_admin
        print("=" * 80)
        print("📋 ПРИЗНАЧЕННЯ АГЕНТІВ ДО alex_admin:")
        print("=" * 80)
        alex_count = 0
        for username in alex_agents:
            agent = User.query.filter_by(username=username, role='agent').first()
            if agent:
                old_admin_id = agent.admin_id
                agent.admin_id = alex_admin.id
                old_admin = User.query.get(old_admin_id).username if old_admin_id else "не призначено"
                print(f"✅ {username:25} → alex_admin (було: {old_admin})")
                alex_count += 1
            else:
                print(f"⚠️ {username:25} - агент не знайдено")
        
        print()
        print(f"✅ Призначено до alex_admin: {alex_count} агентів")
        print()
        
        # Призначаємо всіх інших агентів до anton_admin
        print("=" * 80)
        print("📋 ПРИЗНАЧЕННЯ ВСІХ ІНШИХ АГЕНТІВ ДО anton_admin:")
        print("=" * 80)
        
        # Отримуємо всіх агентів, окрім тих, що вже призначені до alex_admin
        all_agents = User.query.filter_by(role='agent').all()
        anton_count = 0
        
        for agent in all_agents:
            # Пропускаємо агентів, які вже призначені до alex_admin
            if agent.username in alex_agents:
                continue
            
            # Якщо агент не має адміна або має іншого адміна (не alex_admin), призначаємо anton_admin
            if agent.admin_id != alex_admin.id:
                old_admin_id = agent.admin_id
                agent.admin_id = anton_admin.id
                old_admin = User.query.get(old_admin_id).username if old_admin_id else "не призначено"
                print(f"✅ {agent.username:25} → anton_admin (було: {old_admin})")
                anton_count += 1
        
        print()
        print(f"✅ Призначено до anton_admin: {anton_count} агентів")
        print()
        
        # Зберігаємо зміни
        try:
            db.session.commit()
            print("=" * 80)
            print("✅ ВСІ ЗМІНИ ЗБЕРЕЖЕНО!")
            print("=" * 80)
            print()
            
            # Показуємо статистику
            alex_total = User.query.filter_by(role='agent', admin_id=alex_admin.id).count()
            anton_total = User.query.filter_by(role='agent', admin_id=anton_admin.id).count()
            
            print("📊 СТАТИСТИКА:")
            print(f"   alex_admin: {alex_total} агентів")
            print(f"   anton_admin: {anton_total} агентів")
            print("=" * 80)
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Помилка збереження: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    try:
        assign_agents_to_admins()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

