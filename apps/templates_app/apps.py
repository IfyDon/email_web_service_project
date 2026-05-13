# ── apps/templates_app/apps.py ────────────────────────────────────────────────

from django.apps import AppConfig

class TemplatesAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.templates_app"
    label = "templates_app"
