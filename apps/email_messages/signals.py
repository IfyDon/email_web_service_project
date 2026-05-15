"""
Message signals.

Place: apps/email_messages/signals.py
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message


@receiver(post_save, sender=Message)
def on_message_status_change(sender, instance, created, **kwargs):
    """
    After a message transitions to a terminal state,
    update the user's month-to-date sent counter.

    Phase 3.2 will extend this to fire analytics aggregation.
    """
    if not created and instance.status == Message.Status.DELIVERED:
        instance.user.increment_sent(count=1)