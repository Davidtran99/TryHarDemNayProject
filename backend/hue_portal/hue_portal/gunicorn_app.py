"""
Gunicorn application wrapper with post_fork hook for model preloading.
This file serves as both the WSGI application and Gunicorn config.
"""
import os

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")

# Import Django
import django
django.setup()

# Import wsgi application
from hue_portal.hue_portal.wsgi import application


# Define post_fork hook (Gunicorn will call this automatically)
def post_fork(server, worker):
    """Called when worker process is forked - preload models here."""
    print(f"[GUNICORN] 🔔 Worker {worker.pid} forked, preloading models...", flush=True)
    try:
        # Prefer single-level package path
        try:
            from hue_portal.preload_models import preload_all_models
        except ModuleNotFoundError:
            from hue_portal.hue_portal.preload_models import preload_all_models
        preload_all_models()
    except Exception as e:
        print(f"[GUNICORN] ⚠️ Failed to preload models in worker {worker.pid}: {e}", flush=True)
        import traceback

        traceback.print_exc()


# Gunicorn config variables
bind = "0.0.0.0:7860"
timeout = 1800
graceful_timeout = 1800
worker_class = "sync"
