#!/usr/bin/env python3
"""
Оновлення статусів старих лідів на основі hubspot_deal_id
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
    status = db.Column(db.String(50), default='new')
    hubspot_stage_label = db.Column(db.String(100))

def fix_old_leads_status():
    """Оновлює статуси старих лідів на основі hubspot_deal_id"""
    if not hubspot_client:
        print("❌ HubSpot клієнт не доступний!")
        return False
    
    with app.app_context():
        # Отримуємо всі ліди з hubspot_deal_id
        leads = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).all()
        
        print("=" * 80)
        print("🔄 ОНОВЛЕННЯ СТАТУСІВ СТАРИХ ЛІДІВ")
        print("=" * 80)
        print(f"Знайдено лідів з hubspot_deal_id: {len(leads)}")
        print()
        
        # Маппінг стадій HubSpot
        stage_mapping = {
            '3204738258': 'new',        # Новая заявка
            '3204738259': 'contacted',  # Контакт встановлено
            '3204738261': 'qualified',  # Кваліфіковано
            '3204738262': 'qualified',  # Встреча проведена
            '3204738265': 'qualified',  # Переговоры
            '3204738266': 'qualified',  # Задаток
            '3204738267': 'closed'      # Сделка закрыта
        }
        
        stage_labels = {
            '3204738258': 'Запрос получен',
            '3204738259': 'Отправлены варианты/Передан на партнеров',
            '3204738261': 'Назначена встреча/тур',
            '3204738262': 'Встреча/тур проведены',
            '3204738265': 'Переговоры',
            '3204738266': 'Задаток',
            '3204738267': 'Сделка закрыта'
        }
        
        updated_count = 0
        error_count = 0
        
        for lead in leads:
            try:
                # Отримуємо deal з HubSpot
                deal = hubspot_client.crm.deals.basic_api.get_by_id(
                    deal_id=lead.hubspot_deal_id,
                    properties=["dealstage"]
                )
                
                if not deal.properties or not deal.properties.get('dealstage'):
                    continue
                
                dealstage_id = deal.properties['dealstage']
                old_status = lead.status
                old_label = lead.hubspot_stage_label
                
                # Оновлюємо статус
                new_status = None
                new_label = None
                
                if dealstage_id in stage_mapping:
                    new_status = stage_mapping[dealstage_id]
                
                if dealstage_id in stage_labels:
                    new_label = stage_labels[dealstage_id]
                
                # Оновлюємо тільки якщо змінилося
                if new_status and new_status != old_status:
                    lead.status = new_status
                    updated_count += 1
                    print(f"✅ Лід {lead.id}: статус {old_status} → {new_status} (dealstage: {dealstage_id})")
                
                if new_label and new_label != old_label:
                    lead.hubspot_stage_label = new_label
                    if new_status == old_status:
                        updated_count += 1
                    print(f"   Label: {old_label or 'N/A'} → {new_label}")
                    
            except Exception as e:
                error_count += 1
                print(f"❌ Помилка для ліда {lead.id}: {e}")
                continue
        
        # Зберігаємо всі зміни
        if updated_count > 0:
            try:
                db.session.commit()
                print()
                print("=" * 80)
                print(f"✅ ОНОВЛЕНО: {updated_count} лідів")
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
            print("ℹ️ Жодних змін не потрібно")
            print("=" * 80)
            return False

if __name__ == '__main__':
    try:
        fix_old_leads_status()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

