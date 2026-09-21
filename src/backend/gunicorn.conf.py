"""Single-worker Gunicorn configuration for a personal dashboard server."""
import os


bind = "0.0.0.0:5000"
workers = 1
threads = 4
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")


def post_worker_init(worker):
    """Start APScheduler in the sole Gunicorn worker when enabled."""
    app = worker.app.wsgi()
    if app.config.get("SCHEDULER_ENABLED"):
        app.scheduler.start()


def worker_exit(server, worker):
    """Cleanly stop APScheduler during container shutdown."""
    worker.app.wsgi().scheduler.shutdown()