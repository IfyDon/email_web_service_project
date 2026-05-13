# ── apps/email_messages/signals.py ───────────────────────────────────────────
# Save as a SEPARATE file: apps/email_messages/signals.py
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="email_messages.Message")
def on_message_status_change(sender, instance, created, **kwargs):
    if not created and instance.status == "delivered":
        instance.user.increment_sent(count=1)
"""