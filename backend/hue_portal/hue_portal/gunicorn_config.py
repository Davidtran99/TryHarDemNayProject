"""
Gunicorn configuration file with post_fork hook to preload models.
This ensures models are loaded when each worker process starts.
"""
import os
import sys

# Gunicorn config variables
bind = "0.0.0.0:7860"
timeout = 1800
graceful_timeout = 1800
worker_class = "sync"

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    This is where we preload models in each worker process.
    """
    print(f'[GUNICORN] 🔔 Worker {worker.pid} forked, preloading models...', flush=True)
    
    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
    
    # Import Django
    import django
    django.setup()
    
    # Preload models
    try:
        from hue_portal.hue_portal.preload_models import preload_all_models
        preload_all_models()
    except Exception as e:
        print(f'[GUNICORN] ⚠️ Failed to preload models in worker {worker.pid}: {e}', flush=True)
        import traceback
        traceback.print_exc()


This ensures models are loaded when each worker process starts.
"""
import os
import sys

# Gunicorn config variables
bind = "0.0.0.0:7860"
timeout = 1800
graceful_timeout = 1800
worker_class = "sync"

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    This is where we preload models in each worker process.
    """
    print(f'[GUNICORN] 🔔 Worker {worker.pid} forked, preloading models...', flush=True)
    
    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
    
    # Import Django
    import django
    django.setup()
    
    # Preload models
    try:
        from hue_portal.hue_portal.preload_models import preload_all_models
        preload_all_models()
    except Exception as e:
        print(f'[GUNICORN] ⚠️ Failed to preload models in worker {worker.pid}: {e}', flush=True)
        import traceback
        traceback.print_exc()

