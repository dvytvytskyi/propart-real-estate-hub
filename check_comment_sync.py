#!/usr/bin/env python3
"""
Скрипт для перевірки синхронізації коментарів з HubSpot
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Lead, Comment

def check_comment_sync():
    """Перевіряє синхронізацію коментарів з HubSpot"""
    with app.app_context():
        print("=" * 80)
        print("🔍 ПЕРЕВІРКА СИНХРОНІЗАЦІЇ КОМЕНТАРІВ З HUBSPOT")
        print("=" * 80)
        
        # Отримуємо останні коментарі
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(10).all()
        
        if not recent_comments:
            print("❌ Коментарів не знайдено")
            return
        
        print(f"\n📋 Знайдено {len(recent_comments)} останніх коментарів\n")
        
        for comment in recent_comments:
            lead = Lead.query.get(comment.lead_id)
            if not lead:
                print(f"❌ Лід {comment.lead_id} не знайдено для коментаря {comment.id}")
                continue
            
            print(f"📝 Коментар ID: {comment.id}")
            print(f"   Лід: {lead.deal_name} (ID: {lead.id})")
            print(f"   Контент: {comment.content[:50]}...")
            print(f"   Створено: {comment.created_at}")
            print(f"   hubspot_note_id: {comment.hubspot_note_id or '❌ НЕ ВСТАНОВЛЕНО'}")
            print(f"   lead.hubspot_deal_id: {lead.hubspot_deal_id or '❌ НЕ ВСТАНОВЛЕНО'}")
            
            if not lead.hubspot_deal_id:
                print(f"   ⚠️  ПРОБЛЕМА: Лід не має hubspot_deal_id!")
            elif not comment.hubspot_note_id:
                print(f"   ⚠️  ПРОБЛЕМА: Коментар не синхронізовано з HubSpot!")
            else:
                print(f"   ✅ Коментар синхронізовано з HubSpot")
            
            print()
        
        # Статистика
        print("\n📊 СТАТИСТИКА:")
        print("-" * 80)
        total_comments = Comment.query.count()
        synced_comments = Comment.query.filter(Comment.hubspot_note_id.isnot(None)).count()
        unsynced_comments = total_comments - synced_comments
        
        print(f"Всього коментарів: {total_comments}")
        print(f"Синхронізовано: {synced_comments}")
        print(f"Не синхронізовано: {unsynced_comments}")
        
        # Перевірка лідів без hubspot_deal_id
        leads_without_deal_id = Lead.query.filter(Lead.hubspot_deal_id.is_(None)).count()
        leads_with_deal_id = Lead.query.filter(Lead.hubspot_deal_id.isnot(None)).count()
        
        print(f"\nЛіди з hubspot_deal_id: {leads_with_deal_id}")
        print(f"Ліди без hubspot_deal_id: {leads_without_deal_id}")
        
        print("\n" + "=" * 80)
        print("💡 Рекомендації:")
        if unsynced_comments > 0:
            print("   1. Перевірте логи сервера після додавання коментаря")
            print("   2. Перевірте, чи є hubspot_deal_id у ліда")
            print("   3. Перевірте, чи правильно налаштовано HUBSPOT_API_KEY")
        print("=" * 80)

if __name__ == "__main__":
    check_comment_sync()

