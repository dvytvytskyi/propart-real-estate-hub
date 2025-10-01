"""
Gunicorn конфігурація для ProPart Real Estate Hub
Production-ready configuration
"""
import multiprocessing
import os

# Server Socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker Processes
# Формула: (2 × CPU) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 60
graceful_timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/propart/gunicorn_access.log"
errorlog = "/var/log/propart/gunicorn_error.log"
loglevel = "info"
capture_output = True
enable_stdio_inheritance = True
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process Naming
proc_name = "propart_hub"

# Server Mechanics
daemon = False
pidfile = "/var/run/propart/gunicorn.pid"
umask = 0
user = "www-data"
group = "www-data"

# Preload app for better memory usage
preload_app = True

# Restart workers after this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Worker timeouts
timeout = 60
graceful_timeout = 30

# Environment
raw_env = [
    'FLASK_ENV=production',
]

