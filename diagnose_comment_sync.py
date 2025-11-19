#!/usr/bin/env python3
"""
Діагностика проблеми синхронізації коментарів з HubSpot Notes
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, Comment, User, hubspot_client, HUBSPOT_API_KEY

def diagnose_comment_sync():
    """Діагностує проблему синхронізації коментарів"""
    with app.app_context():
        print("=" * 80)
        print("🔍 ДІАГНОСТИКА СИНХРОНІЗАЦІЇ КОМЕНТАРІВ З HUBSPOT")
        print("=" * 80)
        print()
        
        # 1. Перевірка HubSpot клієнта
        print("1️⃣ Перевірка HubSpot клієнта:")
        print(f"   hubspot_client: {hubspot_client is not None}")
        print(f"   HUBSPOT_API_KEY: {'✅ Встановлено' if HUBSPOT_API_KEY else '❌ НЕ ВСТАНОВЛЕНО'}")
        if HUBSPOT_API_KEY:
            print(f"   HUBSPOT_API_KEY (перші 10 символів): {HUBSPOT_API_KEY[:10]}...")
        print()
        
        # 2. Перевірка лідів
        print("2️⃣ Перевірка лідів:")
        total_leads = Lead.query.count()
        leads_with_deal_id = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).count()
        leads_without_deal_id = total_leads - leads_with_deal_id
        
        print(f"   Всього лідів: {total_leads}")
        print(f"   Ліди з hubspot_deal_id: {leads_with_deal_id}")
        print(f"   Ліди без hubspot_deal_id: {leads_without_deal_id}")
        print()
        
        # 3. Перевірка коментарів
        print("3️⃣ Перевірка коментарів:")
        total_comments = Comment.query.count()
        synced_comments = Comment.query.filter(Comment.hubspot_note_id.isnot(None)).count()
        unsynced_comments = total_comments - synced_comments
        
        print(f"   Всього коментарів: {total_comments}")
        print(f"   Синхронізовано: {synced_comments}")
        print(f"   НЕ синхронізовано: {unsynced_comments}")
        print()
        
        # 4. Детальна перевірка несинхронізованих коментарів
        print("4️⃣ Детальна перевірка несинхронізованих коментарів:")
        unsynced = Comment.query.filter(Comment.hubspot_note_id.is_(None)).all()
        
        if unsynced:
            print(f"   Знайдено {len(unsynced)} несинхронізованих коментарів:")
            print()
            
            for comment in unsynced[:10]:  # Показуємо перші 10
                lead = Lead.query.get(comment.lead_id)
                user = User.query.get(comment.user_id)
                
                print(f"   📝 Коментар ID: {comment.id}")
                print(f"      Лід: {lead.deal_name if lead else 'НЕ ЗНАЙДЕНО'} (ID: {comment.lead_id})")
                print(f"      Автор: {user.username if user else 'НЕ ЗНАЙДЕНО'}")
                print(f"      Створено: {comment.created_at}")
                print(f"      hubspot_deal_id: {lead.hubspot_deal_id if lead else '❌ Лід не знайдено'}")
                print(f"      hubspot_note_id: {comment.hubspot_note_id or '❌ НЕ СИНХРОНІЗОВАНО'}")
                
                # Перевірка умов синхронізації
                if lead:
                    conditions_met = []
                    conditions_met.append(("hubspot_deal_id", bool(lead.hubspot_deal_id)))
                    conditions_met.append(("hubspot_client", hubspot_client is not None))
                    conditions_met.append(("HUBSPOT_API_KEY", bool(HUBSPOT_API_KEY)))
                    
                    print(f"      Умови синхронізації:")
                    for condition, met in conditions_met:
                        status = "✅" if met else "❌"
                        print(f"         {status} {condition}: {met}")
                    
                    if all(met for _, met in conditions_met):
                        print(f"      ⚠️  ВСІ УМОВИ ВИКОНАНІ, але коментар не синхронізовано!")
                        print(f"      💡 Можлива проблема: помилка API або помилка в коді")
                else:
                    print(f"      ❌ Лід не знайдено - це критична помилка!")
                
                print()
        else:
            print("   ✅ Всі коментарі синхронізовані!")
        print()
        
        # 5. Перевірка останніх коментарів
        print("5️⃣ Останні 5 коментарів:")
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(5).all()
        
        for comment in recent_comments:
            lead = Lead.query.get(comment.lead_id)
            print(f"   📝 ID: {comment.id}, Лід: {lead.deal_name if lead else 'N/A'}, "
                  f"Створено: {comment.created_at}, "
                  f"hubspot_note_id: {comment.hubspot_note_id or '❌ НЕ СИНХРОНІЗОВАНО'}")
        print()
        
        # 6. Перевірка тестового ліда
        print("6️⃣ Перевірка ліда 'тест комент':")
        test_lead = Lead.query.filter(Lead.deal_name.like("%тест%")).first()
        
        if test_lead:
            print(f"   ✅ Лід знайдено: {test_lead.deal_name} (ID: {test_lead.id})")
            print(f"   hubspot_deal_id: {test_lead.hubspot_deal_id or '❌ НЕ ВСТАНОВЛЕНО'}")
            
            test_comments = Comment.query.filter_by(lead_id=test_lead.id).all()
            print(f"   Коментарів: {len(test_comments)}")
            
            for comment in test_comments:
                print(f"      - ID: {comment.id}, hubspot_note_id: {comment.hubspot_note_id or '❌ НЕ СИНХРОНІЗОВАНО'}")
        else:
            print("   ❌ Лід 'тест комент' не знайдено")
        print()
        
        # 7. Рекомендації
        print("=" * 80)
        print("💡 РЕКОМЕНДАЦІЇ:")
        print("=" * 80)
        
        if not HUBSPOT_API_KEY:
            print("❌ HUBSPOT_API_KEY не встановлено!")
            print("   Виконайте: export HUBSPOT_API_KEY='ваш-ключ'")
            print()
        
        if not hubspot_client:
            print("❌ hubspot_client не ініціалізовано!")
            print("   Перевірте налаштування HubSpot в app.py")
            print()
        
        if leads_without_deal_id > 0:
            print(f"⚠️  {leads_without_deal_id} лідів без hubspot_deal_id")
            print("   Виконайте: python3 sync_lead_to_hubspot.py")
            print()
        
        if unsynced_comments > 0:
            print(f"⚠️  {unsynced_comments} коментарів не синхронізовано")
            print("   Перевірте логи сервера після додавання коментаря")
            print("   Виконайте: sudo journalctl -u propart -f")
            print()
        
        print("=" * 80)

if __name__ == "__main__":
    diagnose_comment_sync()

