#!/usr/bin/env python3
"""
Скрипт для синхронізації існуючого ліда з HubSpot (створення deal, якщо його немає)
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, User

def sync_lead_to_hubspot(lead_id):
    """Синхронізує лід з HubSpot (створює deal, якщо його немає)"""
    with app.app_context():
        lead = Lead.query.get(lead_id)
        
        if not lead:
            print(f"❌ Лід {lead_id} не знайдено")
            return False
        
        print("=" * 80)
        print(f"🔄 СИНХРОНІЗАЦІЯ ЛІДА З HUBSPOT")
        print("=" * 80)
        print(f"Лід: {lead.deal_name} (ID: {lead.id})")
        print(f"Email: {lead.email}")
        print(f"Phone: {lead.phone}")
        print(f"hubspot_deal_id: {lead.hubspot_deal_id or '❌ НЕ ВСТАНОВЛЕНО'}")
        print(f"hubspot_contact_id: {lead.hubspot_contact_id or '❌ НЕ ВСТАНОВЛЕНО'}")
        print()
        
        if lead.hubspot_deal_id:
            print(f"✅ Лід вже має hubspot_deal_id: {lead.hubspot_deal_id}")
            print("   Синхронізація не потрібна")
            return True
        
        from app import hubspot_client, HUBSPOT_API_KEY
        
        if not hubspot_client:
            print("❌ hubspot_client не ініціалізовано")
            return False
        
        if not HUBSPOT_API_KEY:
            print("❌ HUBSPOT_API_KEY не встановлено")
            return False
        
        try:
            # Спочатку створюємо контакт (якщо його немає)
            hubspot_contact_id = lead.hubspot_contact_id
            
            if not hubspot_contact_id:
                print("📝 Створення контакту в HubSpot...")
                from hubspot.crm.contacts import SimplePublicObjectInput
                
                contact_properties = {
                    "email": lead.email,
                }
                
                if lead.phone:
                    contact_properties["phone"] = lead.phone
                
                if lead.company:
                    contact_properties["company"] = lead.company
                
                contact_input = SimplePublicObjectInput(properties=contact_properties)
                hubspot_contact = hubspot_client.crm.contacts.basic_api.create(
                    simple_public_object_input=contact_input
                )
                hubspot_contact_id = str(hubspot_contact.id)
                print(f"✅ Контакт створено в HubSpot: {hubspot_contact_id}")
            else:
                print(f"✅ Контакт вже існує: {hubspot_contact_id}")
            
            # Тепер створюємо deal
            print("📝 Створення deal в HubSpot...")
            
            # Отримуємо агента
            agent = User.query.get(lead.agent_id)
            hubspot_owner_id = None
            
            if agent and agent.email:
                try:
                    owners = hubspot_client.crm.owners.owners_api.get_page()
                    for owner in owners.results:
                        if owner.email and owner.email.lower() == agent.email.lower():
                            hubspot_owner_id = str(owner.id)
                            print(f"✅ Знайдено HubSpot owner ID: {hubspot_owner_id} для {agent.email}")
                            break
                except Exception as owner_error:
                    print(f"⚠️ Помилка пошуку HubSpot owner: {owner_error}")
            
            # Створюємо deal
            deal_properties = {
                "dealname": lead.deal_name,
                "pipeline": "default",
                "dealstage": "appointmentscheduled",
            }
            
            if lead.budget:
                from app import get_budget_value
                deal_properties["amount"] = get_budget_value(lead.budget)
            
            if lead.email:
                deal_properties["email"] = lead.email
            
            if lead.phone:
                deal_properties["phone_number"] = lead.phone
            
            if agent:
                deal_properties["from_agent_portal__name_"] = agent.username
            
            if hubspot_owner_id:
                deal_properties["hubspot_owner_id"] = hubspot_owner_id
            
            from hubspot.crm.deals import SimplePublicObjectInput as DealInput
            deal_input = DealInput(properties=deal_properties)
            hubspot_deal = hubspot_client.crm.deals.basic_api.create(deal_input)
            hubspot_deal_id = str(hubspot_deal.id)
            
            print(f"✅ Deal створено в HubSpot: {hubspot_deal_id}")
            
            # Створюємо зв'язок між контактом та deal
            if hubspot_contact_id:
                try:
                    hubspot_client.crm.associations.basic_api.create(
                        from_object_type="contacts",
                        from_object_id=hubspot_contact_id,
                        to_object_type="deals",
                        to_object_id=hubspot_deal_id,
                        association_type="contact_to_deal"
                    )
                    print(f"✅ Зв'язок між контактом та deal створено")
                except Exception as assoc_error:
                    # Спробуємо альтернативний метод через v4 API
                    try:
                        import requests
                        from app import HUBSPOT_API_KEY
                        url = f"https://api.hubapi.com/crm/v4/objects/contacts/{hubspot_contact_id}/associations/deals/{hubspot_deal_id}"
                        headers = {
                            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                            "Content-Type": "application/json"
                        }
                        response = requests.put(url, headers=headers, json={"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3})
                        if response.status_code in [200, 201]:
                            print(f"✅ Зв'язок між контактом та deal створено (через v4 API)")
                        else:
                            print(f"⚠️ Помилка створення зв'язку через v4 API: {response.status_code} - {response.text}")
                    except Exception as v4_error:
                        print(f"⚠️ Помилка створення зв'язку: {assoc_error}, v4: {v4_error}")
                        # Не критична помилка - контакт і deal вже створені
            
            # Оновлюємо лід
            lead.hubspot_contact_id = hubspot_contact_id
            lead.hubspot_deal_id = hubspot_deal_id
            db.session.commit()
            
            print()
            print("=" * 80)
            print("✅ СИНХРОНІЗАЦІЯ ЗАВЕРШЕНА!")
            print("=" * 80)
            print(f"hubspot_contact_id: {hubspot_contact_id}")
            print(f"hubspot_deal_id: {hubspot_deal_id}")
            print()
            print("💡 Тепер коментарі будуть синхронізуватися з HubSpot!")
            
            return True
            
        except Exception as e:
            print(f"❌ Помилка синхронізації: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        lead_id = int(sys.argv[1])
    else:
        # Знаходимо лід "тест комент"
        with app.app_context():
            lead = Lead.query.filter_by(deal_name="тест комент").first()
            if not lead:
                leads = Lead.query.filter(Lead.deal_name.like("%тест%")).all()
                if leads:
                    lead = leads[0]
            
            if lead:
                lead_id = lead.id
                print(f"Знайдено лід: {lead.deal_name} (ID: {lead.id})")
            else:
                print("❌ Лід не знайдено. Вкажіть ID ліда:")
                print(f"   Використання: python {sys.argv[0]} <lead_id>")
                sys.exit(1)
    
    sync_lead_to_hubspot(lead_id)

