"""
Account signals.
Place: apps/accounts/signals.py
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


def get_user_model_lazy():
    from django.contrib.auth import get_user_model
    return get_user_model()


@receiver(post_save, sender="accounts.User")
def on_user_created(sender, instance, created, **kwargs):
    """
    Post-creation hook.
    Phase 2 will extend this to create a default sending domain slot
    and trigger a welcome email.
    """
    if created:
        pass   # placeholder