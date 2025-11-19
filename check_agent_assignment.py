#!/usr/bin/env python3
"""
Скрипт для перевірки призначення агентів для лідів
Перевіряє:
1. Які агенти призначені локально
2. Що в HubSpot (hubspot_owner_id та from_agent_portal__name_)
3. Чи є невідповідності
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Lead

def check_agent_assignment():
    """Перевіряє призначення агентів для всіх лідів"""
    with app.app_context():
        print("=" * 80)
        print("🔍 ПЕРЕВІРКА ПРИЗНАЧЕННЯ АГЕНТІВ ДЛЯ ЛІДІВ")
        print("=" * 80)
        
        # Отримуємо всіх користувачів
        users = User.query.all()
        user_dict = {u.id: u for u in users}
        
        print(f"\n📋 Користувачі в системі ({len(users)}):")
        for user in users:
            print(f"   ID {user.id}: {user.username} ({user.email}) - {user.role}")
        
        # Отримуємо всі ліди
        leads = Lead.query.all()
        print(f"\n📋 Ліди в системі ({len(leads)}):")
        
        agent_stats = {}
        issues = []
        
        for lead in leads:
            agent = user_dict.get(lead.agent_id)
            agent_name = agent.username if agent else f"НЕЗНАЙДЕНО (ID: {lead.agent_id})"
            
            # Статистика
            if agent_name not in agent_stats:
                agent_stats[agent_name] = 0
            agent_stats[agent_name] += 1
            
            # Перевірка на проблеми
            if not agent:
                issues.append({
                    'lead_id': lead.id,
                    'deal_name': lead.deal_name,
                    'issue': f'Агент з ID {lead.agent_id} не знайдено в системі',
                    'hubspot_deal_id': lead.hubspot_deal_id
                })
            
            # Перевірка на "olena"
            if 'olena' in agent_name.lower():
                issues.append({
                    'lead_id': lead.id,
                    'deal_name': lead.deal_name,
                    'issue': f'Знайдено "olena" в агенті: {agent_name}',
                    'hubspot_deal_id': lead.hubspot_deal_id,
                    'agent_id': lead.agent_id
                })
        
        # Виводимо статистику
        print("\n📊 СТАТИСТИКА ПРИЗНАЧЕННЯ АГЕНТІВ:")
        print("-" * 80)
        for agent_name, count in sorted(agent_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"   {agent_name:<30} : {count:>4} лідів")
        
        # Виводимо проблеми
        if issues:
            print(f"\n⚠️  ЗНАЙДЕНО ПРОБЛЕМ ({len(issues)}):")
            print("-" * 80)
            for issue in issues[:20]:  # Показуємо перші 20
                print(f"   Лід ID {issue['lead_id']}: {issue['deal_name']}")
                print(f"      Проблема: {issue['issue']}")
                if issue.get('hubspot_deal_id'):
                    print(f"      HubSpot Deal ID: {issue['hubspot_deal_id']}")
                print()
            
            if len(issues) > 20:
                print(f"   ... та ще {len(issues) - 20} проблем")
        else:
            print("\n✅ Проблем не знайдено")
        
        # Перевіряємо HubSpot дані (якщо є доступ)
        print("\n" + "=" * 80)
        print("🔍 ПЕРЕВІРКА HUBSPOT ДАНИХ")
        print("=" * 80)
        
        try:
            from app import hubspot_client
            if hubspot_client:
                print("✅ HubSpot API доступний")
                
                # Перевіряємо кілька лідів з HubSpot
                leads_with_hubspot = [l for l in leads if l.hubspot_deal_id][:10]
                
                if leads_with_hubspot:
                    print(f"\n📋 Перевірка {len(leads_with_hubspot)} лідів з HubSpot:")
                    print("-" * 80)
                    
                    for lead in leads_with_hubspot:
                        try:
                            deal = hubspot_client.crm.deals.basic_api.get_by_id(
                                deal_id=lead.hubspot_deal_id,
                                properties=['hubspot_owner_id', 'from_agent_portal__name_', 'dealname']
                            )
                            
                            hubspot_owner_id = deal.properties.get('hubspot_owner_id')
                            from_agent_portal = deal.properties.get('from_agent_portal__name_', '')
                            
                            local_agent = user_dict.get(lead.agent_id)
                            
                            print(f"\n   Лід: {lead.deal_name}")
                            print(f"      Локальний агент: {local_agent.username if local_agent else 'НЕЗНАЙДЕНО'}")
                            print(f"      HubSpot owner_id: {hubspot_owner_id or 'НЕ ВСТАНОВЛЕНО'}")
                            print(f"      from_agent_portal__name_: {from_agent_portal or 'НЕ ВСТАНОВЛЕНО'}")
                            
                            # Перевіряємо owner email
                            if hubspot_owner_id:
                                try:
                                    owner = hubspot_client.crm.owners.owners_api.get_by_id(
                                        owner_id=hubspot_owner_id
                                    )
                                    print(f"      HubSpot owner email: {owner.email if owner else 'НЕЗНАЙДЕНО'}")
                                    
                                    # Перевіряємо, чи є такий користувач
                                    owner_user = User.query.filter_by(email=owner.email).first() if owner and owner.email else None
                                    if owner_user:
                                        print(f"      Користувач з таким email: {owner_user.username} (ID: {owner_user.id})")
                                        if owner_user.id != lead.agent_id:
                                            print(f"      ⚠️  НЕВІДПОВІДНІСТЬ: локальний агент ({local_agent.username if local_agent else 'НЕЗНАЙДЕНО'}) != HubSpot owner ({owner_user.username})")
                                except Exception as owner_error:
                                    print(f"      ⚠️  Помилка отримання owner: {owner_error}")
                            
                            # Перевіряємо from_agent_portal
                            if from_agent_portal:
                                portal_user = User.query.filter_by(username=from_agent_portal.strip()).first()
                                if portal_user:
                                    print(f"      Користувач з from_agent_portal: {portal_user.username} (ID: {portal_user.id})")
                                    if portal_user.id != lead.agent_id:
                                        print(f"      ⚠️  НЕВІДПОВІДНІСТЬ: локальний агент ({local_agent.username if local_agent else 'НЕЗНАЙДЕНО'}) != from_agent_portal ({portal_user.username})")
                                else:
                                    print(f"      ⚠️  Користувач '{from_agent_portal}' не знайдено в системі")
                        
                        except Exception as deal_error:
                            print(f"   ⚠️  Помилка отримання deal {lead.hubspot_deal_id}: {deal_error}")
            else:
                print("⚠️  HubSpot API не налаштований")
        except Exception as e:
            print(f"⚠️  Помилка перевірки HubSpot: {e}")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    check_agent_assignment()

