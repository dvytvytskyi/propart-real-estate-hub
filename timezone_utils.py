"""
Утиліти для роботи з часовим поясом
"""
from datetime import datetime, timezone, timedelta
import pytz

# Налаштовуємо часовий пояс для України
UKRAINE_TZ = pytz.timezone('Europe/Kiev')

def get_ukraine_time():
    """Повертає поточний час в часовому поясі України"""
    return datetime.now(UKRAINE_TZ)

def utc_to_ukraine(utc_datetime):
    """Конвертує UTC час в український час"""
    if utc_datetime is None:
        return None
    
    # Якщо datetime не має timezone, вважаємо його UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.utc.localize(utc_datetime)
    
    # Конвертуємо в український час
    return utc_datetime.astimezone(UKRAINE_TZ)

def ukraine_to_utc(ukraine_datetime):
    """Конвертує український час в UTC"""
    if ukraine_datetime is None:
        return None
    
    # Якщо datetime не має timezone, вважаємо його українським
    if ukraine_datetime.tzinfo is None:
        ukraine_datetime = UKRAINE_TZ.localize(ukraine_datetime)
    
    # Конвертуємо в UTC
    return ukraine_datetime.astimezone(pytz.utc)

def format_ukraine_time(dt, format_str='%d %B %Y %H:%M'):
    """Форматує час в українському часовому поясі"""
    if dt is None:
        return 'Не вказано'
    
    # Конвертуємо в український час
    ukraine_dt = utc_to_ukraine(dt)
    
    # Форматуємо
    return ukraine_dt.strftime(format_str)

def get_current_timestamp():
    """Повертає поточний timestamp в українському часовому поясі"""
    return get_ukraine_time().timestamp()

def parse_hubspot_timestamp(timestamp_ms):
    """Парсить HubSpot timestamp (мілісекунди) в український час"""
    if timestamp_ms is None:
        return None
    
    try:
        # HubSpot timestamp в мілісекундах
        timestamp_seconds = int(timestamp_ms) / 1000
        utc_dt = datetime.fromtimestamp(timestamp_seconds, tz=pytz.utc)
        return utc_to_ukraine(utc_dt)
    except (ValueError, TypeError):
        return None
