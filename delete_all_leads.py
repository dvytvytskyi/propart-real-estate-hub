#!/usr/bin/env python3
"""
Скрипт для видалення всіх лідів з бази даних
ВИКОРИСТОВУВАТИ З ОБЕРЕЖНІСТЮ! Ця дія незворотна!
"""

import os
import sys
from dotenv import load_dotenv

# Додати поточну директорію до шляху
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app import app, db, Lead

def delete_all_leads():
    """Видаляє всі ліди з бази даних"""
    with app.app_context():
        try:
            # Підрахунок перед видаленням
            total_leads = Lead.query.count()
            
            if total_leads == 0:
                print("✅ База даних вже порожня. Лідів немає.")
                return
            
            print(f"⚠️  УВАГА! Буде видалено {total_leads} лідів!")
            print("=" * 60)
            
            # Показати перші 10 лідів для підтвердження
            sample_leads = Lead.query.limit(10).all()
            print("\n📋 Приклад лідів для видалення:")
            for lead in sample_leads:
                print(f"  - {lead.deal_name or 'Без назви'} (ID: {lead.id}, Клієнт: {lead.client_name or 'Не вказано'})")
            
            if total_leads > 10:
                print(f"  ... та ще {total_leads - 10} лідів")
            
            print("\n" + "=" * 60)
            confirmation = input("\n❓ Ви впевнені? Введіть 'ТАК' для підтвердження: ")
            
            if confirmation.upper() != 'ТАК':
                print("❌ Операцію скасовано.")
                return
            
            print("\n🗑️  Видалення лідів...")
            
            # Видалення всіх лідів
            deleted_count = Lead.query.delete()
            db.session.commit()
            
            print(f"\n✅ Успішно видалено {deleted_count} лідів!")
            print("📊 База даних тепер порожня.")
            
            # Перевірка
            remaining = Lead.query.count()
            if remaining == 0:
                print("✅ Перевірка: лідів не залишилося.")
            else:
                print(f"⚠️  Увага: залишилося {remaining} лідів!")
                
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Помилка при видаленні: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🗑️  ВИДАЛЕННЯ ВСІХ ЛІДІВ")
    print("=" * 60)
    delete_all_leads()
    print("\n" + "=" * 60)
    print("✅ Скрипт завершено.")
    print("=" * 60 + "\n")

