import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 1
timeout = 300  # 5 dakika - ilk model indirme için yeterli
worker_class = 'sync'
keepalive = 5
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50
