# ── apps/webhooks/apps.py ─────────────────────────────────────────────────────
# ── apps/webhooks/apps.py ─────────────────────────────────────────────────────

from django.apps import AppConfig

class WebhooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.webhooks"
    label = "webhooks"
