#!/usr/bin/env python3
"""
Діагностика проблеми з відображенням ліди в dashboard агента
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Lead

def debug_agent_dashboard(username):
    """Діагностика dashboard для конкретного агента"""
    
    with app.app_context():
        print("=" * 80)
        print(f"🔍 ДІАГНОСТИКА DASHBOARD ДЛЯ АГЕНТА: {username}")
        print("=" * 80)
        print()
        
        # Знаходимо агента
        agent = User.query.filter_by(username=username).first()
        if not agent:
            print(f"❌ Агент {username} не знайдено!")
            return
        
        print(f"✅ Агент знайдено:")
        print(f"   Username: {agent.username}")
        print(f"   ID: {agent.id} (type: {type(agent.id).__name__})")
        print(f"   Role: {agent.role}")
        print()
        
        # Перевіряємо ліди для цього агента
        agent_id = int(agent.id)
        print(f"🔍 Пошук ліди з agent_id = {agent_id} (type: {type(agent_id).__name__})")
        print()
        
        # Різні способи пошуку
        leads_filter_by = Lead.query.filter_by(agent_id=agent_id).all()
        leads_filter = Lead.query.filter(Lead.agent_id == agent_id).all()
        leads_filter_int = Lead.query.filter(Lead.agent_id == int(agent_id)).all()
        
        print(f"📊 Результати пошуку:")
        print(f"   filter_by(agent_id={agent_id}): {len(leads_filter_by)} лідів")
        print(f"   filter(Lead.agent_id == {agent_id}): {len(leads_filter)} лідів")
        print(f"   filter(Lead.agent_id == int({agent_id})): {len(leads_filter_int)} лідів")
        print()
        
        # Перевіряємо всі ліди та їх agent_id
        print("=" * 80)
        print("📋 ВСІ ЛІДИ В БАЗІ (перші 20):")
        print("=" * 80)
        all_leads = Lead.query.limit(20).all()
        for lead in all_leads:
            agent_for_lead = User.query.get(lead.agent_id) if lead.agent_id else None
            agent_name = agent_for_lead.username if agent_for_lead else "НЕ ЗНАЙДЕНО"
            match = "✅" if lead.agent_id == agent_id else "  "
            print(f"{match} Лід {lead.id:3}: agent_id={str(lead.agent_id):5} (type: {type(lead.agent_id).__name__:6}) | Агент: {agent_name:20} | {lead.deal_name[:40]}")
        
        print()
        print("=" * 80)
        print("📋 ЛІДИ ДЛЯ ЦЬОГО АГЕНТА:")
        print("=" * 80)
        if leads_filter:
            for lead in leads_filter:
                print(f"   ✅ Лід {lead.id}: {lead.deal_name}")
        else:
            print("   ⚠️ Ліди не знайдено!")
        
        print()
        print("=" * 80)
        print("🔍 ДЕТАЛЬНА ПЕРЕВІРКА:")
        print("=" * 80)
        
        # Перевіряємо, чи є ліди з таким agent_id
        raw_query = db.session.execute(
            db.text(f"SELECT COUNT(*) FROM lead WHERE agent_id = :agent_id"),
            {"agent_id": agent_id}
        ).scalar()
        print(f"   SQL запит (agent_id = {agent_id}): {raw_query} лідів")
        
        # Перевіряємо всі можливі agent_id в ліди
        unique_agent_ids = db.session.execute(
            db.text("SELECT DISTINCT agent_id FROM lead WHERE agent_id IS NOT NULL")
        ).fetchall()
        print(f"   Унікальні agent_id в ліди: {[row[0] for row in unique_agent_ids]}")
        print(f"   Чи є {agent_id} в списку: {'✅ ТАК' if agent_id in [row[0] for row in unique_agent_ids] else '❌ НІ'}")
        
        print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = 'a_ustian'  # За замовчуванням
    
    try:
        debug_agent_dashboard(username)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

