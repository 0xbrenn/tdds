import multiprocessing

bind = "127.0.0.1:8000"
workers = 16  # Increase from 9-10 to 16
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 2000  # Increase from 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 60
graceful_timeout = 30
keepalive = 5
preload_app = True
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
proc_name = 'iopn-backend'

# Add these for better performance
backlog = 2048