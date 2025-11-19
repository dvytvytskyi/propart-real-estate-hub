#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки створення note та асоціації з deal в HubSpot
"""

import sys
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, Comment, User

def test_note_creation():
    """Тестує створення note та асоціації з deal"""
    with app.app_context():
        print("=" * 80)
        print("🧪 ТЕСТУВАННЯ СТВОРЕННЯ NOTE ТА АСОЦІАЦІЇ З DEAL")
        print("=" * 80)
        print()
        
        # 1. Перевірка API ключа
        hubspot_api_key = os.getenv('HUBSPOT_API_KEY')
        if not hubspot_api_key:
            print("❌ HUBSPOT_API_KEY не знайдено в .env файлі")
            return False
        
        print(f"✅ HUBSPOT_API_KEY знайдено: {hubspot_api_key[:10]}...")
        print()
        
        # 2. Знаходимо лід з hubspot_deal_id
        lead = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).first()
        if not lead:
            print("❌ Лід з hubspot_deal_id не знайдено")
            print("   Виконайте: python3 sync_lead_to_hubspot.py")
            return False
        
        print(f"✅ Знайдено лід: {lead.deal_name}")
        print(f"   Deal ID: {lead.hubspot_deal_id}")
        print()
        
        # 3. Створюємо тестову note
        print("📝 Створення тестової note в HubSpot...")
        note_body = f"Тестовий коментар з системи - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        url = "https://api.hubapi.com/crm/v3/objects/notes"
        headers = {
            "Authorization": f"Bearer {hubspot_api_key}",
            "Content-Type": "application/json"
        }
        
        note_data = {
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": current_timestamp
            }
        }
        
        print(f"   URL: {url}")
        print(f"   Body: {note_data}")
        print()
        
        try:
            response = requests.post(url, headers=headers, json=note_data, timeout=10)
            print(f"📥 Відповідь HubSpot API: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            print(f"   Body: {response.text[:500]}")
            print()
            
            if response.status_code not in [200, 201]:
                print(f"❌ Помилка створення note: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            response_data = response.json()
            note_id = response_data.get('id')
            
            if not note_id:
                print(f"❌ Note створена, але ID не отримано")
                print(f"   Response: {response_data}")
                return False
            
            print(f"✅ Note створена успішно: {note_id}")
            print()
            
            # 4. Створюємо асоціацію з deal через v3 API
            print("🔗 Створення асоціації note з deal через v3 API...")
            # Правильний формат: PUT /crm/v3/objects/notes/{noteId}/associations/deal/{dealId}/214
            # 214 - це тип асоціації для NOTE_TO_DEAL
            assoc_url = f"https://api.hubapi.com/crm/v3/objects/notes/{note_id}/associations/deal/{lead.hubspot_deal_id}/214"
            
            print(f"   URL: {assoc_url}")
            print(f"   Method: PUT (без body)")
            print()
            
            # PUT запит без body (v3 API)
            assoc_response = requests.put(assoc_url, headers=headers, timeout=10)
            print(f"📥 Відповідь HubSpot API (асоціація): {assoc_response.status_code}")
            print(f"   Body: {assoc_response.text[:500]}")
            print()
            
            if assoc_response.status_code in [200, 201, 204]:
                print(f"✅ Асоціація створена успішно!")
                print()
                print("=" * 80)
                print("✅ ТЕСТ ПРОЙШОВ УСПІШНО!")
                print("=" * 80)
                print(f"Note ID: {note_id}")
                print(f"Deal ID: {lead.hubspot_deal_id}")
                print()
                print("💡 Перевірте в HubSpot:")
                print(f"   1. Відкрийте deal {lead.hubspot_deal_id}")
                print(f"   2. Перейдіть до вкладки 'Notes' або 'Activity'")
                print(f"   3. Має з'явитися note з текстом: '{note_body[:50]}...'")
                return True
            else:
                print(f"❌ Асоціація не вдалася: {assoc_response.status_code}")
                print(f"   Response: {assoc_response.text}")
                return False
                    
        except Exception as e:
            print(f"❌ Помилка: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_note_creation()
    sys.exit(0 if success else 1)

