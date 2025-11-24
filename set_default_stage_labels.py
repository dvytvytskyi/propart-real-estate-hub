#!/usr/bin/env python3
"""
Встановлення дефолтного hubspot_stage_label для лідів без нього
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

def set_default_stage_labels():
    """Встановлює дефолтний hubspot_stage_label для лідів без нього"""
    with app.app_context():
        # Ліди без hubspot_stage_label
        leads_without_label = Lead.query.filter(
            (Lead.hubspot_stage_label.is_(None)) | (Lead.hubspot_stage_label == '')
        ).all()
        
        print("=" * 80)
        print("🔄 ВСТАНОВЛЕННЯ ДЕФОЛТНИХ СТАТУСІВ")
        print("=" * 80)
        print(f"Знайдено лідів без hubspot_stage_label: {len(leads_without_label)}")
        print()
        
        # Маппінг статусів на дефолтні labels
        default_labels = {
            'new': 'Запрос получен',
            'contacted': 'Отправлены варианты/Передан на партнеров',
            'qualified': 'Назначена встреча/тур',
            'closed': 'Сделка закрыта'
        }
        
        updated_count = 0
        
        for lead in leads_without_label:
            if lead.status in default_labels:
                lead.hubspot_stage_label = default_labels[lead.status]
                updated_count += 1
                if updated_count <= 20:  # Показуємо перші 20
                    print(f"✅ Лід {lead.id}: встановлено '{default_labels[lead.status]}' (status: {lead.status})")
        
        if updated_count > 20:
            print(f"  ... і ще {updated_count - 20} лідів")
        
        # Зберігаємо зміни
        if updated_count > 0:
            try:
                db.session.commit()
                print()
                print("=" * 80)
                print(f"✅ ОНОВЛЕНО: {updated_count} лідів")
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
        set_default_stage_labels()
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

