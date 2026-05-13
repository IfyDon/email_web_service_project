# ── apps/inbound/apps.py ──────────────────────────────────────────────────────

from django.apps import AppConfig

class InboundConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.inbound"
    label = "inbound"
