# ── apps/email_messages/apps.py ───────────────────────────────────────────────

from django.apps import AppConfig

class EmailMessagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.email_messages"
    label = "email_messages"

    def ready(self):
        import apps.email_messages.signals  # noqa: F401

