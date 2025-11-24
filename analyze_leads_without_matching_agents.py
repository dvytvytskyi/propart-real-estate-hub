#!/usr/bin/env python3
"""
Аналіз лідів, які не мають відповідних агентів по email HubSpot owner
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

# Імпортуємо HubSpot
HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')
if HUBSPOT_API_KEY:
    from hubspot import HubSpot
    hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
else:
    hubspot_client = None

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
    agent = db.relationship('User', foreign_keys=[agent_id])

def analyze_leads():
    """Аналізує лідів, щоб знайти, які агенти могли бути раніше"""
    if not hubspot_client:
        print("❌ HubSpot клієнт не доступний!")
        return
    
    with app.app_context():
        print("=" * 80)
        print("🔍 АНАЛІЗ ЛІДІВ ТА HUBSPOT OWNERS")
        print("=" * 80)
        print()
        
        # Отримуємо всіх агентів
        all_agents = {a.email.lower(): a for a in User.query.filter_by(role='agent').all()}
        
        # Отримуємо перші 50 лідів з hubspot_deal_id
        leads = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).limit(50).all()
        
        print(f"Перевіряємо перші 50 лідів...")
        print()
        print(f"{'Лід ID':<8} {'Deal ID':<15} {'Поточний агент':<25} {'HubSpot Owner Email':<40} {'Статус':<20}")
        print("-" * 80)
        
        hubspot_owner_emails = {}
        mismatches = []
        
        for lead in leads:
            try:
                deal = hubspot_client.crm.deals.basic_api.get_by_id(
                    deal_id=lead.hubspot_deal_id,
                    properties=["hubspot_owner_id"]
                )
                
                if deal.properties and deal.properties.get('hubspot_owner_id'):
                    owner = hubspot_client.crm.owners.owners_api.get_by_id(
                        owner_id=deal.properties['hubspot_owner_id']
                    )
                    
                    if owner and owner.email:
                        owner_email = owner.email.lower()
                        hubspot_owner_emails[owner_email] = hubspot_owner_emails.get(owner_email, 0) + 1
                        
                        # Перевіряємо, чи є агент з таким email
                        has_agent = owner_email in all_agents
                        current_agent = lead.agent.username if lead.agent else "N/A"
                        
                        status = "✅ Співпадає" if has_agent and lead.agent and lead.agent.email.lower() == owner_email else "❌ Не співпадає"
                        
                        if not has_agent or (lead.agent and lead.agent.email.lower() != owner_email):
                            mismatches.append({
                                'lead_id': lead.id,
                                'deal_id': lead.hubspot_deal_id,
                                'current_agent': current_agent,
                                'hubspot_email': owner_email
                            })
                        
                        print(f"{lead.id:<8} {lead.hubspot_deal_id:<15} {current_agent:<25} {owner_email:<40} {status:<20}")
            except Exception as e:
                pass
        
        print()
        print("=" * 80)
        print("📊 СТАТИСТИКА HUBSPOT OWNER EMAILS:")
        print("=" * 80)
        for email, count in sorted(hubspot_owner_emails.items(), key=lambda x: x[1], reverse=True):
            has_agent = email in all_agents
            agent_name = all_agents[email].username if has_agent else "НЕ ЗНАЙДЕНО"
            print(f"{email:<40} - {count:4} лідів | Агент: {agent_name}")
        
        print()
        print(f"⚠️ Невідповідностей: {len(mismatches)}")

if __name__ == '__main__':
    try:
        analyze_leads()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

