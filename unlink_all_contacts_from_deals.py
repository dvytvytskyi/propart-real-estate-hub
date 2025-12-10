#!/usr/bin/env python3
"""
Скрипт для видалення всіх асоціацій між контактами та deals в HubSpot.
НЕ видаляє самі контакти чи deals, тільки зв'язки між ними.
"""

import sys
import os
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, hubspot_client, HUBSPOT_API_KEY

def get_all_deals():
    """Отримує всі deals з HubSpot"""
    deals = []
    after = None
    page = 0
    
    print("📊 Отримуємо всі deals з HubSpot...")
    
    while True:
        try:
            if after:
                response = hubspot_client.crm.deals.basic_api.get_page(limit=100, after=after)
            else:
                response = hubspot_client.crm.deals.basic_api.get_page(limit=100)
            
            deals.extend(response.results)
            print(f"   Отримано {len(deals)} deals...")
            
            if not response.paging or not response.paging.next:
                break
            
            after = response.paging.next.after
            page += 1
            
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Помилка отримання deals: {e}")
            break
    
    print(f"✅ Всього отримано {len(deals)} deals")
    return deals

def get_associated_contacts(deal_id):
    """Отримує всі контакти, асоційовані з deal"""
    contacts = []
    
    try:
        associations = hubspot_client.crm.associations.basic_api.get_page(
            from_object_type='deals',
            from_object_id=deal_id,
            to_object_type='contacts'
        )
        
        if associations.results:
            contacts = [assoc.to_object_id for assoc in associations.results]
            
    except Exception as e:
        # Якщо немає асоціацій, це нормально
        pass
    
    return contacts

def delete_association(contact_id, deal_id):
    """Видаляє асоціацію між контактом та deal"""
    try:
        # Спробуємо через v4 API DELETE
        import requests
        url = f"https://api.hubapi.com/crm/v4/objects/contacts/{contact_id}/associations/deals/{deal_id}"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 204]:
            return True
        elif response.status_code == 404:
            # Асоціація вже не існує
            return True
        else:
            print(f"   ⚠️ Помилка видалення асоціації: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Помилка видалення асоціації: {e}")
        return False

def unlink_all_contacts_from_deals(dry_run=True):
    """Видаляє всі асоціації між контактами та deals"""
    if not hubspot_client:
        print("❌ hubspot_client не ініціалізовано")
        return
    
    if not HUBSPOT_API_KEY:
        print("❌ HUBSPOT_API_KEY не встановлено")
        return
    
    print("=" * 80)
    print("🔗 ВИДАЛЕННЯ АСОЦІАЦІЙ МІЖ КОНТАКТАМИ ТА DEALS")
    print("=" * 80)
    
    if dry_run:
        print("⚠️ РЕЖИМ ПЕРЕВІРКИ (dry-run) - нічого не буде видалено")
    else:
        print("⚠️ РЕЖИМ ВИДАЛЕННЯ - асоціації будуть видалені!")
    
    print()
    
    # Отримуємо всі deals
    deals = get_all_deals()
    
    total_associations = 0
    deleted_count = 0
    error_count = 0
    
    print()
    print("🔍 Перевіряємо асоціації...")
    
    for i, deal in enumerate(deals, 1):
        deal_id = str(deal.id)
        deal_name = deal.properties.get('dealname', 'N/A') if deal.properties else 'N/A'
        
        # Отримуємо асоційовані контакти
        contacts = get_associated_contacts(deal_id)
        
        if contacts:
            total_associations += len(contacts)
            print(f"[{i}/{len(deals)}] Deal {deal_id} ({deal_name}): {len(contacts)} асоціацій")
            
            for contact_id in contacts:
                if dry_run:
                    print(f"   [DRY-RUN] Було б видалено: contact {contact_id} <-> deal {deal_id}")
                else:
                    if delete_association(contact_id, deal_id):
                        deleted_count += 1
                        print(f"   ✅ Видалено: contact {contact_id} <-> deal {deal_id}")
                    else:
                        error_count += 1
                        print(f"   ❌ Помилка видалення: contact {contact_id} <-> deal {deal_id}")
                    
                    # Rate limiting
                    time.sleep(0.05)
        
        # Rate limiting між deals
        if i % 10 == 0:
            time.sleep(0.2)
    
    print()
    print("=" * 80)
    if dry_run:
        print(f"📊 РЕЗУЛЬТАТИ ПЕРЕВІРКИ:")
        print(f"   Знайдено deals: {len(deals)}")
        print(f"   Знайдено асоціацій: {total_associations}")
        print()
        print("💡 Для реального видалення запустіть з --delete")
    else:
        print(f"📊 РЕЗУЛЬТАТИ:")
        print(f"   Перевірено deals: {len(deals)}")
        print(f"   Знайдено асоціацій: {total_associations}")
        print(f"   Видалено асоціацій: {deleted_count}")
        print(f"   Помилок: {error_count}")
    print("=" * 80)

if __name__ == '__main__':
    dry_run = True
    
    if '--delete' in sys.argv:
        dry_run = False
        print("⚠️ УВАГА: Буде виконано РЕАЛЬНЕ видалення асоціацій!")
        print("   Натисніть Ctrl+C для скасування (через 5 секунд)...")
        time.sleep(5)
    
    with app.app_context():
        unlink_all_contacts_from_deals(dry_run=dry_run)

