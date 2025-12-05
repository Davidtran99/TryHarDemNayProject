from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "hue_portal.core"

    def ready(self):
        from . import signals  # noqa: F401

