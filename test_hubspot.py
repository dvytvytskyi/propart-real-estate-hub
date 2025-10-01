#!/usr/bin/env python3
"""
Тест HubSpot API
"""

from dotenv import load_dotenv
import os
from hubspot import HubSpot

load_dotenv()
api_key = os.getenv('HUBSPOT_API_KEY')

if api_key:
    try:
        client = HubSpot(access_token=api_key)
        
        # Перевіряємо контакти
        print('=== ПЕРЕВІРКА КОНТАКТІВ ===')
        contacts = client.crm.contacts.basic_api.get_page(limit=10)
        print(f'Всього контактів: {len(contacts.results)}')
        for contact in contacts.results:
            print(f'- {contact.properties.get("firstname", "")} {contact.properties.get("lastname", "")} ({contact.properties.get("email", "")})')
        
        print('\n=== ПЕРЕВІРКА УГОД ===')
        deals = client.crm.deals.basic_api.get_page(limit=10)
        print(f'Всього угод: {len(deals.results)}')
        for deal in deals.results:
            print(f'- {deal.properties.get("dealname", "")} (${deal.properties.get("amount", "")})')
            
    except Exception as e:
        print(f'Помилка: {e}')
else:
    print('API ключ не знайдено')
