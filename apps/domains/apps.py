# ── apps/domains/apps.py ──────────────────────────────────────────────────────

from django.apps import AppConfig

class DomainsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.domains"
    label = "domains"

    def ready(self):
        import apps.domains.signals  # noqa: F401
