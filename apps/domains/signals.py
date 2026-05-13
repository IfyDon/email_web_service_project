"""
Domain signals.
Place: apps/domains/signals.py
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="domains.Domain")
def on_domain_created(sender, instance, created, **kwargs):
    """
    After a new domain is saved, schedule an initial DNS verification check
    via Celery (wired in Phase 3).
    """
    if created:
        # Phase 3:
        # from workers.tasks.domains import verify_domain_task
        # verify_domain_task.apply_async(args=[str(instance.pk)], countdown=60)
        pass