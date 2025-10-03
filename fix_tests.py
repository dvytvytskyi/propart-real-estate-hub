#!/usr/bin/env python3
"""
Скрипт для виправлення тестів - додає імпорт моделей з init_db
"""
import re

def fix_test_file(file_path):
    """Виправляє файл тестів"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Паттерн для пошуку методів тестів
    test_method_pattern = r'(def test_[^(]+\([^)]*init_db[^)]*\):\s*"""[^"]*"""\s*)([^d]*?)(user = User\()'
    
    def replace_test_method(match):
        method_def = match.group(1)
        middle_part = match.group(2)
        user_creation = match.group(3)
        
        # Додаємо імпорт моделей
        db_import = "        db, User, Lead, NoteStatus, Activity = init_db\n        \n        "
        
        return method_def + db_import + middle_part + user_creation
    
    # Замінюємо всі виклики User, Lead, NoteStatus, Activity
    content = re.sub(test_method_pattern, replace_test_method, content, flags=re.DOTALL)
    
    # Додаткові заміни для інших випадків
    content = re.sub(r'(\s+)user = User\(', r'\1db, User, Lead, NoteStatus, Activity = init_db\n\1        \n\1user = User(', content)
    content = re.sub(r'(\s+)lead = Lead\(', r'\1db, User, Lead, NoteStatus, Activity = init_db\n\1        \n\1lead = Lead(', content)
    content = re.sub(r'(\s+)note = NoteStatus\(', r'\1db, User, Lead, NoteStatus, Activity = init_db\n\1        \n\1note = NoteStatus(', content)
    content = re.sub(r'(\s+)activity = Activity\(', r'\1db, User, Lead, NoteStatus, Activity = init_db\n\1        \n\1activity = Activity(', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_test_file('tests/test_models.py')
    print("Тести виправлено!")
