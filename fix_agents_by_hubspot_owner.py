#!/usr/bin/env python3
"""
Виправлення агентів для лідів на основі hubspot_owner_id
Синхронізує agent_id з HubSpot owner по email
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///instance/real_estate_agents.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

db = SQLAlchemy(app)

# Імпортуємо HubSpot клієнт
HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')
if HUBSPOT_API_KEY:
    from hubspot import HubSpot
    hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
else:
    hubspot_client = None
    print("⚠️ HUBSPOT_API_KEY не знайдено")

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hubspot_deal_id = db.Column(db.String(50))
    deal_name = db.Column(db.String(100), nullable=False)

def fix_agents_by_hubspot_owner():
    """Виправляє agent_id для всіх лідів на основі hubspot_owner_id"""
    if not hubspot_client:
        print("❌ HubSpot клієнт не доступний!")
        return False
    
    with app.app_context():
        # Отримуємо всі ліди з hubspot_deal_id
        leads = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).all()
        
        print("=" * 80)
        print("🔧 ВИПРАВЛЕННЯ АГЕНТІВ ПО HUBSPOT_OWNER_ID")
        print("=" * 80)
        print(f"Знайдено лідів з hubspot_deal_id: {len(leads)}")
        print()
        
        fixed_count = 0
        not_found_count = 0
        error_count = 0
        
        for lead in leads:
            try:
                # Отримуємо deal з HubSpot
                deal = hubspot_client.crm.deals.basic_api.get_by_id(
                    deal_id=lead.hubspot_deal_id,
                    properties=["hubspot_owner_id"]
                )
                
                if not deal.properties or not deal.properties.get('hubspot_owner_id'):
                    continue
                
                hubspot_owner_id = deal.properties['hubspot_owner_id']
                
                # Отримуємо owner з HubSpot
                owner = hubspot_client.crm.owners.owners_api.get_by_id(
                    owner_id=hubspot_owner_id
                )
                
                if not owner or not owner.email:
                    not_found_count += 1
                    continue
                
                # Шукаємо агента в системі по email
                agent = User.query.filter_by(email=owner.email.lower()).first()
                
                if agent and agent.id != lead.agent_id:
                    old_agent = User.query.get(lead.agent_id)
                    old_agent_name = old_agent.username if old_agent else "N/A"
                    
                    print(f"✅ Лід {lead.id} ({lead.deal_name[:30]}...):")
                    print(f"   Старий агент: {old_agent_name} (ID: {lead.agent_id})")
                    print(f"   Новий агент: {agent.username} (ID: {agent.id}, email: {owner.email})")
                    
                    lead.agent_id = agent.id
                    fixed_count += 1
                elif not agent:
                    print(f"⚠️ Лід {lead.id}: Агент з email {owner.email} не знайдено в системі")
                    not_found_count += 1
                else:
                    # Агент вже правильний
                    pass
                    
            except Exception as e:
                print(f"❌ Помилка для ліда {lead.id}: {e}")
                error_count += 1
                continue
        
        # Зберігаємо всі зміни
        if fixed_count > 0:
            try:
                db.session.commit()
                print()
                print("=" * 80)
                print(f"✅ ВИПРАВЛЕНО: {fixed_count} лідів")
                print(f"⚠️ Не знайдено агентів: {not_found_count}")
                print(f"❌ Помилок: {error_count}")
                print("=" * 80)
                return True
            except Exception as e:
                db.session.rollback()
                print(f"❌ Помилка збереження: {e}")
                return False
        else:
            print()
            print("=" * 80)
            print("ℹ️ Жодних змін не потрібно або не знайдено агентів")
            print("=" * 80)
            return False

if __name__ == '__main__':
    try:
        fix_agents_by_hubspot_owner()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

