"""
Rate Limiter для HubSpot API з retry logic
"""
import time
from functools import wraps
import requests
from flask import current_app

class HubSpotRateLimiter:
    """Rate limiter для HubSpot API (100 requests per 10 seconds)"""
    
    def __init__(self, max_calls=90, period=10):
        """
        Args:
            max_calls: Максимальна кількість викликів (90 для безпеки, ліміт 100)
            period: Період в секундах
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            
            # Видаляємо старі виклики
            self.calls = [c for c in self.calls if c > now - self.period]
            
            # Якщо досягли ліміту - чекаємо
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if current_app:
                    current_app.logger.warning(
                        f"HubSpot rate limit reached, sleeping {sleep_time:.2f}s"
                    )
                time.sleep(sleep_time)
            
            # Додаємо поточний виклик
            self.calls.append(time.time())
            
            # Retry logic з exponential backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        # HubSpot повернув 429 (Too Many Requests)
                        retry_after = int(e.response.headers.get('Retry-After', 60))
                        if current_app:
                            current_app.logger.warning(
                                f"429 error from HubSpot, retry after {retry_after}s (attempt {attempt + 1}/{max_retries})"
                            )
                        
                        if attempt < max_retries - 1:
                            time.sleep(retry_after)
                        else:
                            raise
                    
                    elif e.response.status_code >= 500:
                        # Server error - retry з exponential backoff
                        if attempt < max_retries - 1:
                            sleep_time = 2 ** attempt
                            if current_app:
                                current_app.logger.warning(
                                    f"HubSpot server error {e.response.status_code}, retry in {sleep_time}s"
                                )
                            time.sleep(sleep_time)
                        else:
                            raise
                    else:
                        # Інші HTTP помилки - не retry
                        raise
                
                except requests.exceptions.ConnectionError as e:
                    # Network error - retry з exponential backoff
                    if attempt < max_retries - 1:
                        sleep_time = 2 ** attempt
                        if current_app:
                            current_app.logger.warning(
                                f"HubSpot connection error, retry in {sleep_time}s: {str(e)}"
                            )
                        time.sleep(sleep_time)
                    else:
                        raise
                
                except Exception as e:
                    # Інші помилки - retry якщо не остання спроба
                    if attempt < max_retries - 1:
                        sleep_time = 2 ** attempt
                        if current_app:
                            current_app.logger.error(
                                f"Unexpected error with HubSpot API, retry in {sleep_time}s: {str(e)}"
                            )
                        time.sleep(sleep_time)
                    else:
                        raise
        
        return wrapper

# Створюємо глобальний rate limiter
hubspot_rate_limiter = HubSpotRateLimiter(max_calls=90, period=10)

