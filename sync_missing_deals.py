#!/usr/bin/env python3
"""
Скрипт для синхронізації ліди без deal_id в HubSpot
"""
from app import app, db, Lead, User
from hubspot import HubSpot
from hubspot.crm.deals import SimplePublicObjectInput as DealInput
from hubspot.crm.contacts import PublicObjectSearchRequest
import os
from dotenv import load_dotenv

load_dotenv()

def get_budget_value(budget_str):
    """Конвертує бюджет з рядка в число"""
    if not budget_str:
        return None
    
    budget_str = str(budget_str).lower().strip()
    
    # Видаляємо всі символи, крім цифр
    import re
    numbers = re.findall(r'\d+', budget_str)
    if not numbers:
        return None
    
    # Беремо перше число
    value = int(numbers[0])
    
    # Якщо є "млн" або "million" - множимо на 1000000
    if 'млн' in budget_str or 'million' in budget_str:
        value *= 1000000
    # Якщо є "тис" або "k" - множимо на 1000
    elif 'тис' in budget_str or 'k' in budget_str:
        value *= 1000
    
    return value

def sync_missing_deals():
    """Синхронізує ліди без deal_id в HubSpot"""
    HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')
    if not HUBSPOT_API_KEY:
        print("❌ HUBSPOT_API_KEY не знайдено в змінних середовища")
        return
    
    hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
    
    with app.app_context():
        # Знаходимо ліди з contact_id, але без deal_id
        leads_to_sync = Lead.query.filter(
            Lead.hubspot_contact_id.isnot(None),
            Lead.hubspot_deal_id.is_(None)
        ).all()
        
        print(f"Знайдено {len(leads_to_sync)} ліди без deal_id")
        
        synced_count = 0
        error_count = 0
        
        for lead in leads_to_sync:
            try:
                print(f"\n📋 Обробка ліда {lead.id}: {lead.deal_name}")
                print(f"   Contact ID: {lead.hubspot_contact_id}")
                
                # Отримуємо агента
                agent = User.query.get(lead.agent_id) if lead.agent_id else None
                
                # Отримуємо HubSpot owner ID для агента
                hubspot_owner_id = None
                if agent and agent.email:
                    try:
                        owners = hubspot_client.crm.owners.owners_api.get_page()
                        for owner in owners.results:
                            if owner.email and owner.email.lower() == agent.email.lower():
                                hubspot_owner_id = str(owner.id)
                                print(f"   ✅ Знайдено HubSpot owner ID: {hubspot_owner_id}")
                                break
                    except Exception as owner_error:
                        print(f"   ⚠️ Помилка пошуку HubSpot owner: {owner_error}")
                
                # Створюємо deal
                deal_properties = {
                    "dealname": lead.deal_name,
                    "amount": get_budget_value(lead.budget) if lead.budget else None,
                    "dealtype": "newbusiness",
                    "pipeline": "default",
                    "dealstage": "3204738258",  # Новая заявка
                    "phone_number": lead.phone if lead.phone else None,
                    "from_agent_portal__name_": agent.username if agent else None,
                    "responisble_agent": agent.username if agent else None,
                }
                
                # Додаємо email якщо є
                if lead.email:
                    deal_properties["email"] = lead.email
                
                # Додаємо hubspot_owner_id якщо знайдено
                if hubspot_owner_id:
                    deal_properties["hubspot_owner_id"] = hubspot_owner_id
                
                # Видаляємо None значення
                deal_properties = {k: v for k, v in deal_properties.items() if v is not None}
                
                print(f"   Створюємо deal з властивостями: {deal_properties}")
                deal_input = DealInput(properties=deal_properties)
                hubspot_deal = hubspot_client.crm.deals.basic_api.create(deal_input)
                hubspot_deal_id = str(hubspot_deal.id)
                print(f"   ✅ Deal створено: {hubspot_deal_id}")
                
                # Створюємо зв'язок між контактом та deal
                try:
                    hubspot_client.crm.associations.basic_api.create(
                        from_object_type="contacts",
                        from_object_id=lead.hubspot_contact_id,
                        to_object_type="deals",
                        to_object_id=hubspot_deal_id,
                        association_type="contact_to_deal"
                    )
                    print(f"   ✅ Зв'язок створено")
                except Exception as assoc_error:
                    # Спробуємо через v4 API
                    try:
                        import requests
                        url = f"https://api.hubapi.com/crm/v4/objects/contacts/{lead.hubspot_contact_id}/associations/deals/{hubspot_deal_id}"
                        headers = {
                            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                            "Content-Type": "application/json"
                        }
                        response = requests.put(url, headers=headers, json={"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3})
                        if response.status_code in [200, 201]:
                            print(f"   ✅ Зв'язок створено (через v4 API)")
                        else:
                            print(f"   ⚠️ Помилка створення зв'язку: {response.status_code}")
                    except Exception as v4_error:
                        print(f"   ⚠️ Помилка створення зв'язку: {assoc_error}, v4: {v4_error}")
                
                # Оновлюємо лід
                lead.hubspot_deal_id = hubspot_deal_id
                db.session.commit()
                print(f"   ✅ Лід оновлено з deal_id: {hubspot_deal_id}")
                synced_count += 1
                
            except Exception as e:
                print(f"   ❌ Помилка: {e}")
                error_count += 1
                db.session.rollback()
        
        print(f"\n✅ Синхронізовано: {synced_count}")
        print(f"❌ Помилок: {error_count}")

if __name__ == '__main__':
    sync_missing_deals()

