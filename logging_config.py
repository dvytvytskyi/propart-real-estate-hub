"""
Конфігурація логування для ProPart Real Estate Hub
"""
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    """Налаштування централізованого логування"""
    if not app.debug:
        # Створюємо директорію для логів
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Налаштування file handler з ротацією
        file_handler = RotatingFileHandler(
            'logs/propart.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('ProPart Real Estate Hub startup')
    
    # Також налаштовуємо console handler для development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)

