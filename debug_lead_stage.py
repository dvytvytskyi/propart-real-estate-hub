#!/usr/bin/env python3
"""
Діагностика одного ліда для з'ясування, чому не встановлюється hubspot_stage_label
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
    print("⚠️ HUBSPOT_API_KEY не знайдено")

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    hubspot_deal_id = db.Column(db.String(50))
    hubspot_stage_label = db.Column(db.String(100))
    status = db.Column(db.String(50), default='new')
    deal_name = db.Column(db.String(100))

def debug_lead(lead_id):
    """Діагностика конкретного ліда"""
    if not hubspot_client:
        print("❌ HubSpot клієнт не доступний!")
        return False
    
    with app.app_context():
        lead = Lead.query.get(lead_id)
        if not lead:
            print(f"❌ Лід {lead_id} не знайдено")
            return False
        
        print("=" * 80)
        print(f"🔍 ДІАГНОСТИКА ЛІДА {lead_id}")
        print("=" * 80)
        print(f"Deal ID: {lead.hubspot_deal_id}")
        print(f"Status: {lead.status}")
        print(f"HubSpot Stage Label: {lead.hubspot_stage_label or 'НЕ ВСТАНОВЛЕНО'}")
        print(f"Deal Name: {lead.deal_name}")
        print()
        
        if not lead.hubspot_deal_id:
            print("❌ Лід не має hubspot_deal_id")
            return False
        
        try:
            # Отримуємо deal з HubSpot
            deal = hubspot_client.crm.deals.basic_api.get_by_id(
                deal_id=lead.hubspot_deal_id,
                properties=["dealstage", "dealname"]
            )
            
            print("✅ Deal знайдено в HubSpot")
            print(f"Deal Name в HubSpot: {deal.properties.get('dealname') if deal.properties else 'N/A'}")
            
            if not deal.properties:
                print("❌ Deal не має properties")
                return False
            
            dealstage_id = deal.properties.get('dealstage')
            print(f"Dealstage ID: {dealstage_id}")
            
            if not dealstage_id:
                print("❌ Deal не має dealstage")
                return False
            
            # Маппінг стадій HubSpot
            stage_labels = {
                '3204738258': 'Запрос получен',
                '3204738259': 'Отправлены варианты/Передан на партнеров',
                '3204738261': 'Назначена встреча/тур',
                '3204738262': 'Встреча/тур проведены',
                '3204738265': 'Переговоры',
                '3204738266': 'Задаток',
                '3204738267': 'Сделка закрыта'
            }
            
            stage_mapping = {
                '3204738258': 'new',
                '3204738259': 'contacted',
                '3204738261': 'qualified',
                '3204738262': 'qualified',
                '3204738265': 'qualified',
                '3204738266': 'qualified',
                '3204738267': 'closed'
            }
            
            if dealstage_id in stage_labels:
                new_label = stage_labels[dealstage_id]
                print(f"✅ Знайдено label: {new_label}")
                
                if new_label != lead.hubspot_stage_label:
                    print(f"⚠️ Label не співпадає: DB={lead.hubspot_stage_label}, HubSpot={new_label}")
                    lead.hubspot_stage_label = new_label
                    db.session.commit()
                    print(f"✅ Оновлено hubspot_stage_label: {new_label}")
                else:
                    print(f"✅ Label вже правильний: {new_label}")
            else:
                print(f"⚠️ Dealstage ID {dealstage_id} не знайдено в маппінгу!")
                print(f"   Доступні ID: {list(stage_labels.keys())}")
            
            if dealstage_id in stage_mapping:
                new_status = stage_mapping[dealstage_id]
                print(f"✅ Знайдено status: {new_status}")
                
                if new_status != lead.status:
                    print(f"⚠️ Status не співпадає: DB={lead.status}, HubSpot={new_status}")
                    lead.status = new_status
                    db.session.commit()
                    print(f"✅ Оновлено status: {new_status}")
                else:
                    print(f"✅ Status вже правильний: {new_status}")
            else:
                print(f"⚠️ Dealstage ID {dealstage_id} не знайдено в маппінгу статусів!")
            
        except Exception as e:
            print(f"❌ Помилка: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("=" * 80)
        return True

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        lead_id = int(sys.argv[1])
        debug_lead(lead_id)
    else:
        # Тестуємо перший лід з проблемою
        with app.app_context():
            lead = Lead.query.filter(
                Lead.hubspot_deal_id.isnot(None),
                (Lead.hubspot_stage_label.is_(None)) | (Lead.hubspot_stage_label == '')
            ).first()
            if lead:
                debug_lead(lead.id)
            else:
                print("❌ Не знайдено лідів без hubspot_stage_label")

