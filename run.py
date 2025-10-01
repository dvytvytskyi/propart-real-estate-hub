#!/usr/bin/env python3
"""
Запуск Real Estate Agents Hub додатку
"""

from app import app

if __name__ == '__main__':
    print("🏠 Запуск Real Estate Agents Hub...")
    print("📱 Відкрийте браузер: http://localhost:5001")
    print("🔑 Тестові облікові записи:")
    print("   Адмін: admin / admin123")
    print("   Агент: agent / agent123")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5001)
