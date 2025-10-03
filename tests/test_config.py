"""
Тестова конфігурація для ProPart Real Estate Hub
"""
import os
import tempfile

# Тестова конфігурація
TEST_CONFIG = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'test-secret-key-for-testing-only',
    'WTF_CSRF_ENABLED': False,
    'HUBSPOT_API_KEY': None,  # Вимкнено для тестів
    'SQLALCHEMY_ENGINE_OPTIONS': {
        'pool_pre_ping': True,
    }
}
