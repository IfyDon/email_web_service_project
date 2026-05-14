"""
Suppression list models.

Suppression  – a single suppressed email address (bounce / complaint / unsubscribe).
UnsubscribeToken – signed token embedded in List-Unsubscribe links.

Place: apps/suppressions/models.py
"""

import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import UUIDModel, TimeStampedModel


class Suppression(UUIDModel, TimeStampedModel):
    """
    A suppressed email address for a specific user account.

    Once an address is suppressed, the send service will refuse
    to deliver any further messages to it (enforced pre-queue).

    Reason choices mirror the event types from the ESP:
      - bounce     → hard bounce; address doesn't exist
      - complaint  → recipient clicked "Mark as Spam"
      - unsubscribe→ recipient clicked the unsubscribe link
      - manual     → manually added by the account owner
    """

    class Reason(models.TextChoices):
        BOUNCE      = "bounce",      "Hard Bounce"
        COMPLAINT   = "complaint",   "Spam Complaint"
        UNSUBSCRIBE = "unsubscribe", "Unsubscribed"
        MANUAL      = "manual",      "Manually Added"

    # ── Fields ────────────────────────────────────────────────────────────────
    user          = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suppressions",
        db_index=True,
    )
    email         = models.EmailField(db_index=True)
    email_hash    = models.CharField(
        max_length=64, editable=False,
        help_text="SHA-256 of the lowercase email for fast lookup",
    )
    reason        = models.CharField(
        max_length=15, choices=Reason.choices, default=Reason.MANUAL, db_index=True
    )
    # Source message id that triggered the suppression (nullable for manual)
    source_message_id = models.UUIDField(null=True, blank=True)
    description   = models.TextField(blank=True, help_text="Optional admin note")

    class Meta:
        verbose_name        = "Suppression"
        verbose_name_plural = "Suppressions"
        # One suppression record per user+email (regardless of reason)
        unique_together = [("user", "email_hash")]
        ordering        = ["-created_at"]
        indexes         = [
            models.Index(fields=["user", "email_hash"]),
            models.Index(fields=["user", "reason"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} ({self.reason}) – {self.user.email}"

    def save(self, *args, **kwargs):
        self.email      = self.email.lower().strip()
        self.email_hash = _hash_email(self.email)
        super().save(*args, **kwargs)

    # ── Class helpers ─────────────────────────────────────────────────────────

    @classmethod
    def is_suppressed(cls, user, email: str) -> bool:
        """Fast check: is `email` on this user's suppression list?"""
        return cls.objects.filter(
            user=user, email_hash=_hash_email(email.lower().strip())
        ).exists()

    @classmethod
    def suppress(
        cls,
        user,
        email: str,
        reason: str,
        source_message_id=None,
        description: str = "",
    ) -> "Suppression":
        """
        Add or update a suppression record.
        Uses get_or_create so repeat ESP webhooks are idempotent.
        """
        email = email.lower().strip()
        obj, created = cls.objects.update_or_create(
            user=user,
            email_hash=_hash_email(email),
            defaults={
                "email":             email,
                "reason":            reason,
                "source_message_id": source_message_id,
                "description":       description,
            },
        )
        return obj

    @classmethod
    def remove(cls, user, email: str) -> bool:
        """
        Remove a suppression record (allow sending to this address again).
        Returns True if a record was deleted.
        """
        deleted, _ = cls.objects.filter(
            user=user, email_hash=_hash_email(email.lower().strip())
        ).delete()
        return deleted > 0


class UnsubscribeToken(UUIDModel):
    """
    A signed, single-use token embedded in List-Unsubscribe links.

    Format: /unsubscribe/<token>/
    On visit: mark token used + add email to Suppression list.
    """

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="unsubscribe_tokens",
    )
    email      = models.EmailField()
    token      = models.CharField(max_length=64, unique=True, editable=False)
    message_id = models.UUIDField(null=True, blank=True)
    used       = models.BooleanField(default=False)
    used_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Unsubscribe Token"
        ordering     = ["-created_at"]

    def __str__(self) -> str:
        return f"Unsubscribe token for {self.email}"

    @classmethod
    def create(cls, user, email: str, message_id=None) -> "UnsubscribeToken":
        """Generate a fresh unsubscribe token for an outgoing message."""
        return cls.objects.create(
            user=user,
            email=email.lower().strip(),
            token=secrets.token_urlsafe(48),
            message_id=message_id,
        )

    def consume(self) -> bool:
        """Mark token used and suppress the email. Returns False if already used."""
        if self.used:
            return False
        self.used    = True
        self.used_at = timezone.now()
        self.save(update_fields=["used", "used_at"])

        Suppression.suppress(
            user=self.user,
            email=self.email,
            reason=Suppression.Reason.UNSUBSCRIBE,
            source_message_id=self.message_id,
        )
        return True


# ── Internal helpers ──────────────────────────────────────────────────────────

def _hash_email(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()