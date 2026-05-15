"""
Email message models.

Message      – the canonical record for every outgoing email.
MessageAttempt – each delivery attempt (tracks retry history).

Place: apps/email_messages/models.py
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import UUIDModel, TimeStampedModel, OwnedModel


class Message(UUIDModel, TimeStampedModel, OwnedModel):
    """
    One email send request (single recipient).

    Bulk sends expand each recipient into its own Message row so
    every delivery can be tracked independently.
    """

    class Status(models.TextChoices):
        QUEUED    = "queued",    "Queued"
        SENDING   = "sending",  "Sending"
        DELIVERED = "delivered","Delivered"
        OPENED    = "opened",   "Opened"
        CLICKED   = "clicked",  "Clicked"
        BOUNCED   = "bounced",  "Bounced"
        COMPLAINED= "complained","Complained"
        FAILED    = "failed",   "Failed"

    # ── Addressing ────────────────────────────────────────────────────────────
    from_email    = models.EmailField()
    from_name     = models.CharField(max_length=255, blank=True)
    to_email      = models.EmailField(db_index=True)
    to_name       = models.CharField(max_length=255, blank=True)
    reply_to      = models.EmailField(blank=True)

    # ── Content ───────────────────────────────────────────────────────────────
    subject       = models.CharField(max_length=998)
    body_html     = models.TextField(blank=True)
    body_text     = models.TextField(blank=True)

    # Optional references
    template      = models.ForeignKey(
        "templates_app.EmailTemplate",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )
    domain        = models.ForeignKey(
        "domains.Domain",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )

    # ── Tags / metadata (arbitrary key-value for the sender) ─────────────────
    tags          = models.JSONField(default=list, blank=True)
    metadata      = models.JSONField(default=dict, blank=True)

    # ── Delivery status ───────────────────────────────────────────────────────
    status        = models.CharField(
        max_length=12, choices=Status.choices,
        default=Status.QUEUED, db_index=True,
    )
    esp_message_id = models.CharField(
        max_length=255, blank=True,
        help_text="Message ID returned by the ESP (SES, Mailgun, etc.)",
    )

    # ── Retry tracking ────────────────────────────────────────────────────────
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts  = models.PositiveSmallIntegerField(default=5)
    next_attempt  = models.DateTimeField(null=True, blank=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    queued_at     = models.DateTimeField(default=timezone.now)
    sent_at       = models.DateTimeField(null=True, blank=True)
    delivered_at  = models.DateTimeField(null=True, blank=True)

    # ── Celery task ID (for status lookup) ────────────────────────────────────
    celery_task_id = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name        = "Message"
        verbose_name_plural = "Messages"
        ordering            = ["-created_at"]
        indexes             = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["to_email"]),
            models.Index(fields=["esp_message_id"]),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.subject} → {self.to_email}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        """True once the message can no longer be retried."""
        return self.status in (
            self.Status.DELIVERED,
            self.Status.BOUNCED,
            self.Status.COMPLAINED,
            self.Status.FAILED,
        )

    @property
    def retries_exhausted(self) -> bool:
        return self.attempt_count >= self.max_attempts

    def mark_sending(self) -> None:
        self.status = self.Status.SENDING
        self.attempt_count += 1
        self.save(update_fields=["status", "attempt_count", "updated_at"])

    def mark_sent(self, esp_message_id: str = "") -> None:
        now = timezone.now()
        self.status        = self.Status.DELIVERED
        self.esp_message_id = esp_message_id
        self.sent_at       = now
        self.delivered_at  = now
        self.save(update_fields=[
            "status", "esp_message_id", "sent_at", "delivered_at", "updated_at"
        ])

    def mark_failed(self, schedule_retry: bool = True) -> None:
        """Mark failed; optionally schedule exponential-backoff retry."""
        import math
        if self.retries_exhausted:
            self.status = self.Status.FAILED
            self.next_attempt = None
        else:
            self.status = self.Status.QUEUED
            # 5 ^ attempt_count seconds: 5s, 25s, 125s, 625s, 3125s
            delay = int(math.pow(5, self.attempt_count))
            self.next_attempt = timezone.now() + timezone.timedelta(seconds=delay)
        self.save(update_fields=["status", "next_attempt", "updated_at"])

    def mark_bounced(self) -> None:
        self.status = self.Status.BOUNCED
        self.save(update_fields=["status", "updated_at"])

    def mark_complained(self) -> None:
        self.status = self.Status.COMPLAINED
        self.save(update_fields=["status", "updated_at"])


class MessageAttempt(UUIDModel):
    """
    Immutable record of each delivery attempt for a Message.
    Created by the Celery task before each send attempt.
    """

    message    = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attempts"
    )
    attempt_no = models.PositiveSmallIntegerField()
    success    = models.BooleanField(default=False)
    error      = models.TextField(blank=True)
    esp_response = models.JSONField(default=dict, blank=True)
    attempted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name        = "Message Attempt"
        verbose_name_plural = "Message Attempts"
        ordering            = ["-attempted_at"]
        unique_together     = [("message", "attempt_no")]

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"{status} Attempt #{self.attempt_no} for {self.message_id}"