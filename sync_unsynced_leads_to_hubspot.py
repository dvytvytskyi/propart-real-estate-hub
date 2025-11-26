#!/usr/bin/env python3
"""
Синхронізація ліди, які не синхронізувалися з HubSpot
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, User

def sync_unsynced_leads():
    """Синхронізує ліди, які не мають hubspot_contact_id або hubspot_deal_id"""
    
    with app.app_context():
        print("=" * 80)
        print("🔄 СИНХРОНІЗАЦІЯ ЛІДИ БЕЗ HUBSPOT ID")
        print("=" * 80)
        print()
        
        # Знаходимо ліди без HubSpot ID
        unsynced_leads = Lead.query.filter(
            (Lead.hubspot_contact_id.is_(None)) | (Lead.hubspot_deal_id.is_(None))
        ).all()
        
        print(f"📊 Знайдено {len(unsynced_leads)} ліди без HubSpot синхронізації")
        print()
        
        if len(unsynced_leads) == 0:
            print("✅ Всі ліди синхронізовані з HubSpot!")
            return
        
        # Імпортуємо функцію синхронізації
        from sync_lead_to_hubspot import sync_lead_to_hubspot
        
        synced_count = 0
        error_count = 0
        
        for lead in unsynced_leads:
            print(f"🔄 Синхронізація ліда {lead.id}: {lead.deal_name}")
            print(f"   Email: {lead.email}")
            print(f"   Phone: {lead.phone}")
            print(f"   hubspot_contact_id: {lead.hubspot_contact_id or 'НЕ ВСТАНОВЛЕНО'}")
            print(f"   hubspot_deal_id: {lead.hubspot_deal_id or 'НЕ ВСТАНОВЛЕНО'}")
            
            try:
                success = sync_lead_to_hubspot(lead.id)
                if success:
                    # Оновлюємо лід з БД
                    db.session.refresh(lead)
                    print(f"   ✅ Синхронізовано! Contact: {lead.hubspot_contact_id}, Deal: {lead.hubspot_deal_id}")
                    synced_count += 1
                else:
                    print(f"   ❌ Помилка синхронізації")
                    error_count += 1
            except Exception as e:
                print(f"   ❌ Помилка: {e}")
                error_count += 1
            
            print()
        
        print("=" * 80)
        print("📊 РЕЗУЛЬТАТИ:")
        print(f"   Синхронізовано: {synced_count}")
        print(f"   Помилок: {error_count}")
        print("=" * 80)

if __name__ == '__main__':
    try:
        sync_unsynced_leads()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

