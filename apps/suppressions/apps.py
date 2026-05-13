# ── apps/suppressions/apps.py ─────────────────────────────────────────────────

from django.apps import AppConfig

class SuppressionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.suppressions"
    label = "suppressions"
