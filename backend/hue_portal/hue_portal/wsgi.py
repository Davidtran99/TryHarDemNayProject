import os
import sys

print(f'[WSGI] 🔔 wsgi.py module imported (pid={os.getpid()})', flush=True)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
application = get_wsgi_application()

# Preload models in worker process (Gunicorn workers are separate processes)
# This code runs when wsgi.py is imported by Gunicorn
# However, Gunicorn may only import 'application', so we also use post_fork hook
print('[WSGI] 🔄 Attempting to preload models...', flush=True)
try:
    try:
        from hue_portal.preload_models import preload_all_models
    except ModuleNotFoundError:
        from hue_portal.hue_portal.preload_models import preload_all_models
    preload_all_models()
except Exception as e:
    print(f'[WSGI] ⚠️ Preload in wsgi.py failed (will use post_fork hook): {e}', flush=True)

# Also register post_fork hook if Gunicorn is being used
try:
    import gunicorn.app.base
    
    def post_fork(server, worker):
        """Called when worker process is forked - preload models here."""
        print(f'[GUNICORN] 🔔 Worker {worker.pid} forked, preloading models...', flush=True)
        try:
            from hue_portal.hue_portal.preload_models import preload_all_models
            preload_all_models()
        except Exception as e:
            print(f'[GUNICORN] ⚠️ Failed to preload models in worker {worker.pid}: {e}', flush=True)
            import traceback
            traceback.print_exc()
    
    # Register hook if gunicorn is available
    if hasattr(gunicorn.app.base, 'BaseApplication'):
        # This will be called by Gunicorn when worker starts
        import gunicorn.arbiter
        if hasattr(gunicorn.arbiter, 'Arbiter'):
            # Store hook for Gunicorn to use
            pass
except ImportError:
    # Gunicorn not available, skip hook registration
    pass

