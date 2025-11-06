#!/usr/bin/env python3
"""
Скрипт для отримання списку всіх pipelines з HubSpot API
"""
import os
from hubspot import HubSpot
from dotenv import load_dotenv

# Завантажуємо змінні середовища
load_dotenv()

HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')

if not HUBSPOT_API_KEY:
    print("❌ HUBSPOT_API_KEY не знайдено в змінних середовища")
    print("Переконайтеся, що файл .env містить HUBSPOT_API_KEY=pat-...")
    exit(1)

try:
    hubspot_client = HubSpot(access_token=HUBSPOT_API_KEY)
    print("✅ HubSpot API підключено\n")
except Exception as e:
    print(f"❌ Помилка підключення до HubSpot API: {e}")
    exit(1)

try:
    print("🔍 Отримуємо всі pipelines для deals...\n")
    pipelines = hubspot_client.crm.pipelines.pipelines_api.get_all(object_type='deals')
    
    print("=" * 80)
    print("📋 СПИСОК ВСІХ PIPELINES:")
    print("=" * 80)
    
    for idx, pipeline in enumerate(pipelines.results, 1):
        print(f"\n{idx}. Pipeline:")
        print(f"   ID: {pipeline.id}")
        print(f"   Label: {pipeline.label}")
        print(f"   Display Order: {getattr(pipeline, 'display_order', 'N/A')}")
        print(f"   Archived: {getattr(pipeline, 'archived', False)}")
        
        if pipeline.stages:
            print(f"   Stages ({len(pipeline.stages)}):")
            for stage_idx, stage in enumerate(pipeline.stages, 1):
                print(f"      {stage_idx}. {stage.label}")
                print(f"         ID: {stage.id}")
                print(f"         Display Order: {stage.display_order}")
        else:
            print("   Stages: немає")
        
        print("-" * 80)
    
    print(f"\n✅ Всього знайдено pipelines: {len(pipelines.results)}")
    
    # Шукаємо pipeline з stage "appointmentscheduled"
    print("\n" + "=" * 80)
    print("🔍 ПОШУК PIPELINE З STAGE 'appointmentscheduled':")
    print("=" * 80)
    
    found = False
    for pipeline in pipelines.results:
        if pipeline.stages:
            for stage in pipeline.stages:
                if stage.id == 'appointmentscheduled':
                    print(f"\n✅ Знайдено!")
                    print(f"   Pipeline ID: {pipeline.id}")
                    print(f"   Pipeline Label: {pipeline.label}")
                    print(f"   Stage ID: {stage.id}")
                    print(f"   Stage Label: {stage.label}")
                    found = True
                    break
            if found:
                break
    
    if not found:
        print("\n⚠️ Pipeline з stage 'appointmentscheduled' не знайдено")
        print("Перевірте, чи правильно вказано stage ID")
    
except Exception as e:
    print(f"\n❌ Помилка отримання pipelines: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

