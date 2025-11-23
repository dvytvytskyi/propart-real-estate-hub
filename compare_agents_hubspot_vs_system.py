#!/usr/bin/env python3
"""
Порівняння агентів з HubSpot та нашої системи
Показує які агенти є в HubSpot, які в нашій системі, та які відповідають
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
    agent = db.relationship('User', foreign_keys=[agent_id])

def compare_agents():
    """Порівнює агентів з HubSpot та нашої системи"""
    if not hubspot_client:
        print("❌ HubSpot клієнт не доступний!")
        return
    
    with app.app_context():
        print("=" * 80)
        print("🔍 ПОРІВНЯННЯ АГЕНТІВ: HUBSPOT vs НАША СИСТЕМА")
        print("=" * 80)
        print()
        
        # Отримуємо агентів з нашої системи
        our_agents = User.query.filter_by(role='agent').order_by(User.username).all()
        our_admins = User.query.filter_by(role='admin').order_by(User.username).all()
        
        print("📋 АГЕНТИ В НАШІЙ СИСТЕМІ:")
        print("-" * 80)
        print(f"{'ID':<5} {'Логін':<25} {'Email':<40}")
        print("-" * 80)
        for agent in our_agents:
            print(f"{agent.id:<5} {agent.username:<25} {agent.email:<40}")
        print()
        
        print("👑 АДМІНИ В НАШІЙ СИСТЕМІ:")
        print("-" * 80)
        print(f"{'ID':<5} {'Логін':<25} {'Email':<40}")
        print("-" * 80)
        for admin in our_admins:
            print(f"{admin.id:<5} {admin.username:<25} {admin.email:<40}")
        print()
        
        # Отримуємо owners з HubSpot
        print("📋 OWNERS В HUBSPOT:")
        print("-" * 80)
        try:
            owners = hubspot_client.crm.owners.owners_api.get_page()
            hubspot_owners = []
            
            print(f"{'ID':<15} {'Ім\'я':<30} {'Email':<40}")
            print("-" * 80)
            
            for owner in owners.results:
                owner_name = ""
                if owner.first_name and owner.last_name:
                    owner_name = f"{owner.first_name} {owner.last_name}"
                elif owner.first_name:
                    owner_name = owner.first_name
                elif owner.last_name:
                    owner_name = owner.last_name
                else:
                    owner_name = "N/A"
                
                email = owner.email or "N/A"
                hubspot_owners.append({
                    'id': str(owner.id),
                    'name': owner_name,
                    'email': email.lower() if email != "N/A" else None
                })
                
                print(f"{str(owner.id):<15} {owner_name:<30} {email:<40}")
            
            print()
            print(f"Всього owners в HubSpot: {len(hubspot_owners)}")
            print()
            
            # Порівняння
            print("=" * 80)
            print("🔍 ПОРІВНЯННЯ:")
            print("=" * 80)
            print()
            
            # Знаходимо відповідності
            matches = []
            hubspot_only = []
            system_only = []
            
            # Перевіряємо кожного HubSpot owner
            for hubspot_owner in hubspot_owners:
                if not hubspot_owner['email']:
                    continue
                
                # Шукаємо в наших агентах
                found = False
                for agent in our_agents + our_admins:
                    if agent.email.lower() == hubspot_owner['email']:
                        matches.append({
                            'hubspot': hubspot_owner,
                            'system': agent
                        })
                        found = True
                        break
                
                if not found:
                    hubspot_only.append(hubspot_owner)
            
            # Знаходимо агентів, яких немає в HubSpot
            hubspot_emails = {o['email'] for o in hubspot_owners if o['email']}
            for agent in our_agents + our_admins:
                if agent.email.lower() not in hubspot_emails:
                    system_only.append(agent)
            
            print("✅ ВІДПОВІДНОСТІ (є і в HubSpot, і в нашій системі):")
            print("-" * 80)
            if matches:
                print(f"{'HubSpot ID':<15} {'HubSpot Name':<30} {'System Username':<25} {'Email':<40}")
                print("-" * 80)
                for match in matches:
                    print(f"{match['hubspot']['id']:<15} {match['hubspot']['name']:<30} {match['system'].username:<25} {match['system'].email:<40}")
            else:
                print("  Не знайдено відповідностей")
            print()
            
            print("⚠️ ТІЛЬКИ В HUBSPOT (немає в нашій системі):")
            print("-" * 80)
            if hubspot_only:
                print(f"{'HubSpot ID':<15} {'Ім\'я':<30} {'Email':<40}")
                print("-" * 80)
                for owner in hubspot_only:
                    print(f"{owner['id']:<15} {owner['name']:<30} {owner['email'] or 'N/A':<40}")
            else:
                print("  Всі HubSpot owners є в нашій системі")
            print()
            
            print("⚠️ ТІЛЬКИ В НАШІЙ СИСТЕМІ (немає в HubSpot):")
            print("-" * 80)
            if system_only:
                print(f"{'ID':<5} {'Логін':<25} {'Email':<40}")
                print("-" * 80)
                for agent in system_only:
                    print(f"{agent.id:<5} {agent.username:<25} {agent.email:<40}")
            else:
                print("  Всі наші агенти є в HubSpot")
            print()
            
            # Перевірка лідів
            print("=" * 80)
            print("📊 ПЕРЕВІРКА ЛІДІВ:")
            print("=" * 80)
            print()
            
            # Отримуємо ліди з hubspot_deal_id
            leads = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).limit(20).all()
            
            print(f"Перевірка перших 20 лідів з hubspot_deal_id:")
            print("-" * 80)
            print(f"{'Лід ID':<8} {'Deal ID':<15} {'Агент в системі':<25} {'Email агента':<40}")
            print("-" * 80)
            
            for lead in leads:
                agent_email = lead.agent.email if lead.agent else "N/A"
                print(f"{lead.id:<8} {lead.hubspot_deal_id:<15} {lead.agent.username if lead.agent else 'N/A':<25} {agent_email:<40}")
            
        except Exception as e:
            print(f"❌ Помилка отримання owners з HubSpot: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    try:
        compare_agents()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

