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
            # ВИМКНЕНО: Створення контактів відключено
            # Контакти більше не створюються і не асоціюються з deals
            hubspot_contact_id = None
            print("⚠️ Створення контактів вимкнено - створюємо тільки deal")
            
            # ВИМКНЕНО: Створення deals відключено
            print("⚠️ Створення deals в HubSpot відключено")
            hubspot_deal_id = None
            
            # Старий код створення deals (закоментовано):
            """
            # Створюємо deal
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
            """
            
            # ВИМКНЕНО: Створення асоціацій між контактами та deals відключено
            # Асоціації більше не створюються
            
            # Оновлюємо лід (ВИМКНЕНО - deals не створюються)
            # lead.hubspot_contact_id = hubspot_contact_id  # ВИМКНЕНО
            # lead.hubspot_deal_id = hubspot_deal_id  # ВИМКНЕНО
            # db.session.commit()  # ВИМКНЕНО
            
            print()
            print("=" * 80)
            print("⚠️ СИНХРОНІЗАЦІЯ НЕ ВИКОНАНА!")
            print("=" * 80)
            print("⚠️ Створення deals в HubSpot відключено")
            print()
            print("💡 Лід збережено локально, але синхронізація з HubSpot не виконана")
            
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

