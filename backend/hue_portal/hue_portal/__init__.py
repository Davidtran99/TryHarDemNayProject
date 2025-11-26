# Optional celery import - only needed for background tasks
# Skip if celery is not available or causes circular import
try:
    from .celery import app as celery_app
    __all__ = ["celery_app"]
except (ImportError, AttributeError) as e:
    # Celery not available or circular import - not needed for Space deployment
    celery_app = None
    __all__ = []


