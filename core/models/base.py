"""
Abstract base models inherited by all domain models.

Place: core/models/base.py
"""

import uuid
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Adds created_at / updated_at to any model.
    All domain models should inherit from this.
    """

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Replaces the default integer PK with a UUID.
    Combine with TimeStampedModel for the full base:

        class MyModel(UUIDModel, TimeStampedModel):
            ...
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class OwnedModel(models.Model):
    """
    Ties a model to a user (owner).
    Provides a standard `user` FK + manager helper.
    """

    from django.conf import settings

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,
    )

    class Meta:
        abstract = True