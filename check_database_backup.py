#!/usr/bin/env python3
"""
Перевірка, чи є резервні копії бази даних
"""

import os
import sys
import glob

print("=" * 80)
print("🔍 ПОШУК РЕЗЕРВНИХ КОПІЙ БАЗИ ДАНИХ")
print("=" * 80)
print()

# Можливі місця резервних копій
backup_locations = [
    '/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/instance/',
    '/home/pro-part-agent/htdocs/agent.pro-part.online/propart-real-estate-hub/',
    '/var/backups/',
    '/root/backups/',
]

print("Можливі файли резервних копій:")
print("-" * 80)
print("На локальній машині:")
if os.path.exists('instance/propart.db'):
    stat = os.stat('instance/propart.db')
    import datetime
    mod_time = datetime.datetime.fromtimestamp(stat.st_mtime)
    size = stat.st_size / 1024 / 1024  # MB
    print(f"  ✅ instance/propart.db ({size:.2f} MB, змінено: {mod_time})")

# Перевірка git історії
print()
print("Git історія змін app.py (останні 10 комітів):")
print("-" * 80)
os.system("git log --oneline -10 -- app.py")

print()
print("=" * 80)
print("💡 РЕКОМЕНДАЦІЇ:")
print("=" * 80)
print("1. Перевірте, чи є резервні копії БД на сервері")
print("2. Подивіться git diff між різними комітами")
print("3. Перевірте, чи не було видалення агентів")

