"""
Gunicorn конфігурація для ProPart Real Estate Hub
"""
import multiprocessing

# Server Socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker Processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/propart/gunicorn_access.log"
errorlog = "/var/log/propart/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process Naming
proc_name = "propart_hub"

# Server Mechanics
daemon = False
pidfile = "/var/run/propart/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (якщо потрібно termination на Gunicorn)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

