#!/usr/bin/env python3
"""
Перевірка всіх лідів в системі
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Lead

def check_all_leads():
    """Перевіряє всі ліди в системі"""
    with app.app_context():
        print("=" * 80)
        print("🔍 ПЕРЕВІРКА ВСІХ ЛІДІВ")
        print("=" * 80)
        
        all_leads = Lead.query.all()
        users = User.query.all()
        user_dict = {u.id: u for u in users}
        
        print(f"\n📊 ЗАГАЛЬНА СТАТИСТИКА:")
        print(f"   Всього лідів: {len(all_leads)}")
        print(f"   З HubSpot deal_id: {Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).count()}")
        print(f"   Без HubSpot deal_id: {Lead.query.filter(Lead.hubspot_deal_id.is_(None)).count()}")
        
        # Статистика по агентах
        agent_stats = {}
        olena_leads = []
        
        for lead in all_leads:
            agent = user_dict.get(lead.agent_id)
            agent_name = agent.username if agent else f"НЕЗНАЙДЕНО (ID: {lead.agent_id})"
            
            if agent_name not in agent_stats:
                agent_stats[agent_name] = []
            agent_stats[agent_name].append(lead)
            
            if 'olena' in agent_name.lower():
                olena_leads.append(lead)
        
        print(f"\n📊 СТАТИСТИКА ПО АГЕНТАХ:")
        print("-" * 80)
        for agent_name, leads_list in sorted(agent_stats.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"   {agent_name:<30} : {len(leads_list):>4} лідів")
        
        # Показуємо приклади лідів на Олені
        if olena_leads:
            print(f"\n⚠️  ЛІДИ ПРИЗНАЧЕНІ НА ОЛЕНУ ({len(olena_leads)}):")
            print("-" * 80)
            for lead in olena_leads[:20]:
                print(f"   Лід {lead.id}: {lead.deal_name}")
                if lead.hubspot_deal_id:
                    print(f"      HubSpot Deal ID: {lead.hubspot_deal_id}")
                else:
                    print(f"      ⚠️  Немає HubSpot Deal ID")
            if len(olena_leads) > 20:
                print(f"   ... та ще {len(olena_leads) - 20} лідів")
        
        print("\n" + "=" * 80)

if __name__ == "__main__":
    check_all_leads()

