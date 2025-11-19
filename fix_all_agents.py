#!/usr/bin/env python3
"""
Скрипт для виправлення призначення агентів для ВСІХ лідів
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Lead

def fix_all_agents(dry_run=True):
    """Виправляє призначення агентів для всіх лідів"""
    with app.app_context():
        from app import hubspot_client
        
        if not hubspot_client:
            print("❌ HubSpot API не налаштований")
            return
        
        print("=" * 80)
        print(f"🔧 ВИПРАВЛЕННЯ ПРИЗНАЧЕННЯ АГЕНТІВ ДЛЯ ВСІХ ЛІДІВ (DRY RUN: {dry_run})")
        print("=" * 80)
        
        # Отримуємо ВСІ ліди
        all_leads = Lead.query.all()
        
        print(f"\n📋 Знайдено {len(all_leads)} лідів в системі")
        
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
        
        fixed_count = 0
        error_count = 0
        skipped_count = 0
        olena_count = 0
        
        # Спочатку обробляємо ліди з HubSpot deal_id
        leads_with_hubspot = [l for l in all_leads if l.hubspot_deal_id]
        print(f"📋 Ліди з HubSpot deal_id: {len(leads_with_hubspot)}")
        
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
                    
                    # Спочатку шукаємо точне співпадіння username
                    agent_user = User.query.filter_by(username=agent_name).first()
                    
                    # Якщо не знайдено, перевіряємо маппінг
                    if not agent_user and agent_name in name_mapping:
                        mapped_username = name_mapping[agent_name]
                        agent_user = User.query.filter_by(username=mapped_username).first()
                    
                    if agent_user:
                        new_agent_id = agent_user.id
                        agent_source = f"from_agent_portal__name_ ({agent_name} → {agent_user.username})"
                        
                        # Рахуємо скільки на Олену
                        if agent_user.username == 'olena_birovchak':
                            olena_count += 1
                
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
                        pass
                
                # Якщо знайдено нового агента і він відрізняється від поточного
                if new_agent_id and new_agent_id != lead.agent_id:
                    new_agent = User.query.get(new_agent_id)
                    
                    if not dry_run:
                        lead.agent_id = new_agent_id
                        db.session.commit()
                        fixed_count += 1
                    else:
                        fixed_count += 1
                else:
                    skipped_count += 1
            
            except Exception as e:
                error_count += 1
                db.session.rollback()
                if "404" not in str(e):  # Не показуємо помилки 404
                    print(f"❌ Помилка обробки ліда {lead.id}: {e}")
        
        print("\n" + "=" * 80)
        print("📊 РЕЗУЛЬТАТИ:")
        print(f"   Виправлено: {fixed_count}")
        print(f"   Пропущено: {skipped_count}")
        print(f"   Помилок: {error_count}")
        print(f"   Призначено на Олену: {olena_count}")
        print("=" * 80)
        
        # Показуємо статистику по агентах
        print("\n📊 ПОТОЧНА СТАТИСТИКА ПО АГЕНТАХ:")
        print("-" * 80)
        users = User.query.all()
        user_dict = {u.id: u for u in users}
        agent_stats = {}
        
        for lead in all_leads:
            agent = user_dict.get(lead.agent_id)
            agent_name = agent.username if agent else f"НЕЗНАЙДЕНО (ID: {lead.agent_id})"
            if agent_name not in agent_stats:
                agent_stats[agent_name] = 0
            agent_stats[agent_name] += 1
        
        for agent_name, count in sorted(agent_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {agent_name:<30} : {count:>4} лідів")
        
        print("=" * 80)
        
        if dry_run:
            print("\n💡 Для застосування змін запустіть з параметром --apply:")
            print("   python fix_all_agents.py --apply")

if __name__ == "__main__":
    dry_run = '--apply' not in sys.argv
    fix_all_agents(dry_run=dry_run)

