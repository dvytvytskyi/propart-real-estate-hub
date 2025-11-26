#!/usr/bin/env python3
"""
Перевірка та виправлення agent_id для ліди
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Lead

def check_and_fix_agent_ids():
    """Перевіряє та виправляє agent_id для ліди"""
    
    with app.app_context():
        print("=" * 80)
        print("🔍 ПЕРЕВІРКА ТА ВИПРАВЛЕННЯ agent_id ДЛЯ ЛІДИ")
        print("=" * 80)
        print()
        
        # Перевіряємо всі ліди
        all_leads = Lead.query.all()
        print(f"📊 Всього ліди: {len(all_leads)}")
        print()
        
        # Перевіряємо ліди з NULL agent_id
        null_agent_leads = Lead.query.filter(Lead.agent_id.is_(None)).all()
        print(f"⚠️ Ліди з NULL agent_id: {len(null_agent_leads)}")
        for lead in null_agent_leads:
            print(f"   - Лід {lead.id}: {lead.deal_name} (agent_id = None)")
        print()
        
        # Перевіряємо ліди з неіснуючими agent_id
        invalid_agent_leads = []
        for lead in all_leads:
            if lead.agent_id:
                agent = User.query.get(lead.agent_id)
                if not agent:
                    invalid_agent_leads.append(lead)
        
        print(f"⚠️ Ліди з неіснуючими agent_id: {len(invalid_agent_leads)}")
        for lead in invalid_agent_leads:
            print(f"   - Лід {lead.id}: {lead.deal_name} (agent_id = {lead.agent_id} - не існує)")
        print()
        
        # Перевіряємо ліди по агентах
        print("=" * 80)
        print("📋 ЛІДИ ПО АГЕНТАХ:")
        print("=" * 80)
        
        agents = User.query.filter_by(role='agent').all()
        for agent in agents:
            agent_leads = Lead.query.filter(Lead.agent_id == agent.id).all()
            print(f"{agent.username:25} (ID: {agent.id:3}): {len(agent_leads):3} лідів")
            if len(agent_leads) == 0:
                print(f"   ⚠️ Немає ліди!")
        
        print()
        print("=" * 80)
        
        # Показуємо приклад ліди для перевірки
        print("📋 ПРИКЛАДИ ЛІДИ (перші 10):")
        print("=" * 80)
        sample_leads = Lead.query.limit(10).all()
        for lead in sample_leads:
            agent = User.query.get(lead.agent_id) if lead.agent_id else None
            agent_name = agent.username if agent else "НЕ ЗНАЙДЕНО"
            print(f"Лід {lead.id:3}: {lead.deal_name[:40]:40} | agent_id: {str(lead.agent_id):5} | Агент: {agent_name}")
        
        print("=" * 80)

if __name__ == '__main__':
    try:
        check_and_fix_agent_ids()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

