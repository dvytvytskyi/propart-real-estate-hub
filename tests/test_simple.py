"""
Простий тест для перевірки налаштувань
"""
import pytest


def test_simple():
    """Простий тест"""
    assert 1 + 1 == 2


def test_user_creation_simple(init_db, sample_user_data):
    """Простий тест створення користувача"""
    db, User, Lead, NoteStatus, Activity = init_db
    
    user = User(
        username=sample_user_data['username'],
        email=sample_user_data['email'],
        role=sample_user_data['role']
    )
    
    assert user.username == sample_user_data['username']
    assert user.email == sample_user_data['email']
    assert user.role == sample_user_data['role']
