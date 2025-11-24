#!/usr/bin/env python3
"""
Перевірка лідів без hubspot_stage_label
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

class Lead(db.Model):
    __tablename__ = 'lead'
    id = db.Column(db.Integer, primary_key=True)
    hubspot_deal_id = db.Column(db.String(50))
    hubspot_stage_label = db.Column(db.String(100))
    status = db.Column(db.String(50), default='new')
    deal_name = db.Column(db.String(100))
    email = db.Column(db.String(120))

def check_leads_without_stage_label():
    """Перевіряє ліди без hubspot_stage_label"""
    with app.app_context():
        # Всі ліди
        all_leads = Lead.query.all()
        
        # Ліди без hubspot_stage_label
        leads_without_label = Lead.query.filter(
            (Lead.hubspot_stage_label.is_(None)) | (Lead.hubspot_stage_label == '')
        ).all()
        
        # Ліди без hubspot_deal_id
        leads_without_deal_id = Lead.query.filter(
            Lead.hubspot_deal_id.is_(None)
        ).all()
        
        # Ліди з hubspot_deal_id, але без hubspot_stage_label
        leads_with_deal_but_no_label = Lead.query.filter(
            Lead.hubspot_deal_id.isnot(None),
            (Lead.hubspot_stage_label.is_(None)) | (Lead.hubspot_stage_label == '')
        ).all()
        
        print("=" * 80)
        print("📊 СТАТИСТИКА ЛІДІВ")
        print("=" * 80)
        print(f"Всього лідів: {len(all_leads)}")
        print(f"Лідів без hubspot_stage_label: {len(leads_without_label)}")
        print(f"Лідів без hubspot_deal_id: {len(leads_without_deal_id)}")
        print(f"Лідів з hubspot_deal_id, але без hubspot_stage_label: {len(leads_with_deal_but_no_label)}")
        print()
        
        if leads_with_deal_but_no_label:
            print("=" * 80)
            print("⚠️ ЛІДИ З HUBSPOT_DEAL_ID, АЛЕ БЕЗ HUBSPOT_STAGE_LABEL:")
            print("=" * 80)
            for lead in leads_with_deal_but_no_label[:20]:  # Показуємо перші 20
                print(f"  - Лід {lead.id}: deal_id={lead.hubspot_deal_id}, status={lead.status}, deal_name={lead.deal_name[:50] if lead.deal_name else 'N/A'}")
            if len(leads_with_deal_but_no_label) > 20:
                print(f"  ... і ще {len(leads_with_deal_but_no_label) - 20} лідів")
            print()
        
        if leads_without_deal_id:
            print("=" * 80)
            print("⚠️ ЛІДИ БЕЗ HUBSPOT_DEAL_ID (не можуть синхронізуватися):")
            print("=" * 80)
            print(f"  Всього: {len(leads_without_deal_id)}")
            print(f"  Ці ліди не мають зв'язку з HubSpot, тому не можуть отримати статус")
            print()
        
        print("=" * 80)
        print("💡 РЕКОМЕНДАЦІЇ:")
        print("=" * 80)
        if leads_with_deal_but_no_label:
            print(f"  1. Запустіть скрипт sync_all_leads_status.py для синхронізації {len(leads_with_deal_but_no_label)} лідів")
        if leads_without_deal_id:
            print(f"  2. {len(leads_without_deal_id)} лідів не мають hubspot_deal_id - вони не можуть синхронізуватися")
            print("     Можливо, ці ліди були створені локально без синхронізації з HubSpot")
        print("=" * 80)

if __name__ == '__main__':
    try:
        check_leads_without_stage_label()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

