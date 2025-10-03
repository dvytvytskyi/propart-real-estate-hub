#!/usr/bin/env python3
"""
Скрипт для запуску тестів ProPart Real Estate Hub
"""
import os
import sys
import subprocess
import argparse

def run_tests(test_type=None, verbose=False, coverage=False):
    """Запускає тести"""
    
    # Базові команди pytest
    cmd = ['python', '-m', 'pytest']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=app',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov'
        ])
    
    # Додаємо маркери залежно від типу тестів
    if test_type == 'models':
        cmd.extend(['-m', 'database', 'tests/test_models.py', 'tests/test_migrations.py'])
    elif test_type == 'unit':
        cmd.extend(['-m', 'unit'])
    elif test_type == 'integration':
        cmd.extend(['-m', 'integration'])
    elif test_type == 'auth':
        cmd.extend(['-m', 'auth'])
    elif test_type == 'hubspot':
        cmd.extend(['-m', 'hubspot'])
    else:
        # Запускаємо всі тести
        cmd.append('tests/')
    
    print(f"🚀 Запуск тестів: {' '.join(cmd)}")
    print("=" * 60)
    
    # Запускаємо тести
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    
    if result.returncode == 0:
        print("\n✅ Всі тести пройшли успішно!")
    else:
        print("\n❌ Деякі тести не пройшли!")
    
    return result.returncode

def install_test_requirements():
    """Встановлює залежності для тестування"""
    print("📦 Встановлення залежностей для тестування...")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements-test.txt'
        ], check=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        print("✅ Залежності для тестування встановлено!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Помилка встановлення залежностей: {e}")
        return False

def main():
    """Головна функція"""
    parser = argparse.ArgumentParser(description='Запуск тестів ProPart Real Estate Hub')
    parser.add_argument('--type', choices=['models', 'unit', 'integration', 'auth', 'hubspot'], 
                       help='Тип тестів для запуску')
    parser.add_argument('--install', action='store_true', 
                       help='Встановити залежності для тестування')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Детальний вивід')
    parser.add_argument('--coverage', action='store_true', 
                       help='Звіт про покриття коду')
    
    args = parser.parse_args()
    
    print("🏠 ProPart Real Estate Hub - Тестування")
    print("=" * 50)
    
    if args.install:
        if not install_test_requirements():
            return 1
    
    # Перевіряємо, чи встановлені залежності
    try:
        import pytest
    except ImportError:
        print("❌ pytest не встановлений. Запустіть з --install")
        return 1
    
    return run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )

if __name__ == '__main__':
    sys.exit(main())
