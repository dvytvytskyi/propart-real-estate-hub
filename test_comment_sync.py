#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки створення коментарів в HubSpot
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, Comment, User

def test_comment_creation():
    """Тестує створення коментаря"""
    with app.app_context():
        from app import hubspot_client, HUBSPOT_API_KEY
        
        if not hubspot_client:
            print("❌ HubSpot API не налаштований")
            return
        
        # Знаходимо лід з HubSpot deal_id
        lead = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).first()
        
        if not lead:
            print("❌ Не знайдено лідів з HubSpot deal_id")
            return
        
        print(f"✅ Знайдено лід: {lead.deal_name} (HubSpot Deal ID: {lead.hubspot_deal_id})")
        
        # Перевіряємо останні коментарі
        comments = Comment.query.filter_by(lead_id=lead.id).order_by(Comment.created_at.desc()).limit(5).all()
        
        print(f"\n📋 Останні коментарі для цього ліда ({len(comments)}):")
        for comment in comments:
            print(f"   ID {comment.id}: {comment.content[:50]}...")
            print(f"      HubSpot Note ID: {comment.hubspot_note_id or 'НЕ СИНХРОНІЗОВАНО'}")
            print(f"      Створено: {comment.created_at}")
            print()
        
        # Перевіряємо, чи є коментарі без HubSpot note_id
        unsynced = Comment.query.filter_by(lead_id=lead.id, hubspot_note_id=None).all()
        if unsynced:
            print(f"⚠️  Знайдено {len(unsynced)} коментарів без HubSpot note_id:")
            for comment in unsynced:
                print(f"   ID {comment.id}: {comment.content[:50]}...")
        else:
            print("✅ Всі коментарі синхронізовані з HubSpot")

if __name__ == "__main__":
    test_comment_creation()

