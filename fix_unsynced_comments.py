#!/usr/bin/env python3
"""
Скрипт для виправлення коментарів, які не синхронізовані з HubSpot
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, Comment, User
import requests

def fix_unsynced_comments(dry_run=True):
    """Виправляє коментарі, які не синхронізовані з HubSpot"""
    with app.app_context():
        from app import hubspot_client, HUBSPOT_API_KEY
        
        if not hubspot_client or not HUBSPOT_API_KEY:
            print("❌ HubSpot API не налаштований")
            return
        
        print("=" * 80)
        print(f"🔧 ВИПРАВЛЕННЯ НЕСИНХРОНІЗОВАНИХ КОМЕНТАРІВ (DRY RUN: {dry_run})")
        print("=" * 80)
        
        # Знаходимо коментарі без hubspot_note_id для лідів з HubSpot deal_id
        unsynced_comments = db.session.query(Comment).join(Lead).filter(
            Comment.hubspot_note_id.is_(None),
            Lead.hubspot_deal_id.isnot(None)
        ).all()
        
        print(f"\n📋 Знайдено {len(unsynced_comments)} коментарів без HubSpot note_id")
        
        if not unsynced_comments:
            print("✅ Всі коментарі синхронізовані!")
            return
        
        fixed_count = 0
        error_count = 0
        
        for comment in unsynced_comments:
            try:
                lead = comment.lead
                user = comment.user
                
                print(f"\n📝 Коментар ID {comment.id} для ліда {lead.deal_name} (Deal ID: {lead.hubspot_deal_id})")
                print(f"   Текст: {comment.content[:50]}...")
                print(f"   Автор: {user.username} ({user.email})")
                print(f"   Створено: {comment.created_at}")
                
                if not dry_run:
                    # Створюємо нотатку в HubSpot
                    from datetime import datetime, timezone
                    
                    url = "https://api.hubapi.com/crm/v3/objects/notes"
                    headers = {
                        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    current_timestamp = comment.created_at.replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if comment.created_at else datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                    
                    note_data = {
                        "properties": {
                            "hs_note_body": comment.content,
                            "hs_timestamp": current_timestamp
                        }
                    }
                    
                    response = requests.post(url, headers=headers, json=note_data)
                    
                    if response.status_code in [200, 201]:
                        response_data = response.json()
                        hubspot_note_id = response_data.get('id')
                        
                        if hubspot_note_id:
                            comment.hubspot_note_id = str(hubspot_note_id)
                            
                            # Створюємо асоціацію з deal
                            assoc_url = f"https://api.hubapi.com/crm/v4/objects/notes/{hubspot_note_id}/associations/deal/{lead.hubspot_deal_id}"
                            assoc_data = [{
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 214
                            }]
                            assoc_response = requests.put(assoc_url, headers=headers, json=assoc_data)
                            
                            if assoc_response.status_code in [200, 201, 204]:
                                db.session.commit()
                                print(f"   ✅ Синхронізовано з HubSpot: {hubspot_note_id}")
                                fixed_count += 1
                            else:
                                print(f"   ⚠️ Нотатка створена, але асоціація не вдалася: {assoc_response.status_code}")
                                db.session.commit()
                                fixed_count += 1  # Все одно вважаємо успішним
                        else:
                            print(f"   ❌ Нотатка створена, але ID не отримано")
                            error_count += 1
                    else:
                        print(f"   ❌ Помилка створення нотатки: {response.status_code} - {response.text[:200]}")
                        error_count += 1
                else:
                    print(f"   ⏸️  Буде синхронізовано (dry run)")
                    fixed_count += 1
            
            except Exception as e:
                print(f"   ❌ Помилка: {e}")
                error_count += 1
                db.session.rollback()
        
        print("\n" + "=" * 80)
        print("📊 РЕЗУЛЬТАТИ:")
        print(f"   Виправлено: {fixed_count}")
        print(f"   Помилок: {error_count}")
        print("=" * 80)
        
        if dry_run:
            print("\n💡 Для застосування змін запустіть з параметром --apply:")
            print("   python fix_unsynced_comments.py --apply")

if __name__ == "__main__":
    dry_run = '--apply' not in sys.argv
    fix_unsynced_comments(dry_run=dry_run)

