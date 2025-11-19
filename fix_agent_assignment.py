#!/usr/bin/env python3
"""
Скрипт для виправлення призначення агентів для лідів на основі HubSpot даних
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Lead

def fix_agent_assignment(dry_run=True):
    """Виправляє призначення агентів на основі HubSpot даних"""
    with app.app_context():
        from app import hubspot_client
        
        if not hubspot_client:
            print("❌ HubSpot API не налаштований")
            return
        
        print("=" * 80)
        print(f"🔧 ВИПРАВЛЕННЯ ПРИЗНАЧЕННЯ АГЕНТІВ (DRY RUN: {dry_run})")
        print("=" * 80)
        
        # Отримуємо всі ліди з HubSpot deal_id
        leads_with_hubspot = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).all()
        
        print(f"\n📋 Знайдено {len(leads_with_hubspot)} лідів з HubSpot deal_id")
        
        fixed_count = 0
        error_count = 0
        skipped_count = 0
        
        for lead in leads_with_hubspot:
            try:
                # Отримуємо deal з HubSpot
                deal = hubspot_client.crm.deals.basic_api.get_by_id(
                    deal_id=lead.hubspot_deal_id,
                    properties=['hubspot_owner_id', 'from_agent_portal__name_', 'dealname']
                )
                
                deal_properties = deal.properties
                current_agent = User.query.get(lead.agent_id)
                
                # Оновлюємо об'єкт lead з бази
                db.session.refresh(lead)
                
                # Пріоритет 1: from_agent_portal__name_
                new_agent_id = None
                agent_source = None
                
                if deal_properties.get('from_agent_portal__name_'):
                    agent_name = deal_properties['from_agent_portal__name_'].strip()
                    
                    # Маппінг різних варіантів імен на username
                    name_mapping = {
                        'Олена Біровчак': 'olena_birovchak',
                        'Бировчак Лена': 'olena_birovchak',
                        'Біровчак Олена': 'olena_birovchak',
                        'Олена Бировчак': 'olena_birovchak',
                        'Бировчак Олена': 'olena_birovchak',
                        'Устьян': 'ustyan',
                        'Новиков Александр': 'alexander_novikov',
                        'Александр Новиков': 'alexander_novikov',
                        'UIK': 'uik',
                        'Благовест': 'blagovest',
                        'Timonov': 'timonov',
                        'Gorzhiy': 'gorzhiy',
                        'Людмила Богданенко': 'lyudmila_bogdanenko',
                        'Александр Лисовенко': 'alexander_lysovenko',
                        'Янина': 'yanina',
                    }
                    
                    # Спочатку шукаємо точне співпадіння username
                    agent_user = User.query.filter_by(username=agent_name).first()
                    
                    # Якщо не знайдено, перевіряємо маппінг
                    if not agent_user and agent_name in name_mapping:
                        mapped_username = name_mapping[agent_name]
                        agent_user = User.query.filter_by(username=mapped_username).first()
                    
                    if agent_user:
                        new_agent_id = agent_user.id
                        agent_source = f"from_agent_portal__name_ ({agent_name} → {agent_user.username})"
                    else:
                        print(f"⚠️  Лід {lead.id} ({lead.deal_name}): користувач '{agent_name}' не знайдено в системі")
                
                # Пріоритет 2: hubspot_owner_id email
                if not new_agent_id and deal_properties.get('hubspot_owner_id'):
                    try:
                        owner = hubspot_client.crm.owners.owners_api.get_by_id(
                            owner_id=deal_properties['hubspot_owner_id']
                        )
                        if owner and owner.email:
                            owner_user = User.query.filter_by(email=owner.email.lower()).first()
                            if owner_user:
                                new_agent_id = owner_user.id
                                agent_source = f"hubspot_owner_id email ({owner.email})"
                    except Exception as owner_error:
                        print(f"⚠️  Помилка отримання owner для ліда {lead.id}: {owner_error}")
                
                # Якщо знайдено нового агента і він відрізняється від поточного
                if new_agent_id and new_agent_id != lead.agent_id:
                    new_agent = User.query.get(new_agent_id)
                    print(f"\n🔄 Лід {lead.id} ({lead.deal_name}):")
                    print(f"   Поточний агент: {current_agent.username if current_agent else 'НЕЗНАЙДЕНО'} (ID: {lead.agent_id})")
                    print(f"   Новий агент: {new_agent.username} (ID: {new_agent_id})")
                    print(f"   Джерело: {agent_source}")
                    
                    if not dry_run:
                        lead.agent_id = new_agent_id
                        db.session.commit()
                        print(f"   ✅ Виправлено!")
                        fixed_count += 1
                    else:
                        print(f"   ⏸️  Буде виправлено (dry run)")
                        fixed_count += 1
                else:
                    skipped_count += 1
            
            except Exception as e:
                print(f"❌ Помилка обробки ліда {lead.id}: {e}")
                db.session.rollback()
                error_count += 1
        
        print("\n" + "=" * 80)
        print("📊 РЕЗУЛЬТАТИ:")
        print(f"   Виправлено: {fixed_count}")
        print(f"   Пропущено: {skipped_count}")
        print(f"   Помилок: {error_count}")
        print("=" * 80)
        
        if dry_run:
            print("\n💡 Для застосування змін запустіть з параметром --apply:")
            print("   python fix_agent_assignment.py --apply")

if __name__ == "__main__":
    dry_run = '--apply' not in sys.argv
    fix_agent_assignment(dry_run=dry_run)

