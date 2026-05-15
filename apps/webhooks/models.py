"""
Webhook models.

Webhook         – a user-configured endpoint URL + event subscriptions.
WebhookDelivery – immutable log of every outbound webhook attempt.

Place: apps/webhooks/models.py
"""

import hashlib
import hmac
import json
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import UUIDModel, TimeStampedModel, OwnedModel


# ── Event type choices (mirrors MessageEvent.EventType) ───────────────────────

ALL_EVENT_TYPES = [
    "delivered",
    "opened",
    "clicked",
    "bounced",
    "complained",
    "unsubscribed",
    "failed",
]


class Webhook(UUIDModel, TimeStampedModel, OwnedModel):
    """
    A user-registered endpoint that receives POST notifications
    for selected email lifecycle events.
    """

    # ── Fields ────────────────────────────────────────────────────────────────
    label      = models.CharField(max_length=200)
    url        = models.URLField(max_length=2048, help_text="HTTPS endpoint URL")

    # Shared secret for HMAC-SHA256 signing of the payload
    # Stored in plain text (it's a shared secret the user needs to read back)
    secret     = models.CharField(
        max_length=64,
        default=secrets.token_hex,
        help_text="HMAC-SHA256 signing secret — expose once via API on creation",
    )

    # JSON array of event type strings the endpoint subscribes to
    # e.g. ["delivered", "bounced", "complained"]
    # Empty list = subscribe to all events
    event_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Event types to deliver. Empty = all events.",
    )

    is_active  = models.BooleanField(default=True)

    # Delivery stats (denormalised for quick dashboard display)
    total_deliveries = models.PositiveIntegerField(default=0)
    failed_deliveries = models.PositiveIntegerField(default=0)
    last_triggered   = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = "Webhook"
        verbose_name_plural = "Webhooks"
        ordering            = ["-created_at"]
        indexes             = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.label} → {self.url[:60]}"

    # ── Subscription helpers ──────────────────────────────────────────────────

    def subscribes_to(self, event_type: str) -> bool:
        """
        Return True if this webhook should receive `event_type`.
        Empty event_types list means subscribe to all.
        """
        if not self.event_types:
            return True
        return event_type in self.event_types

    # ── HMAC signing ──────────────────────────────────────────────────────────

    def sign_payload(self, payload_bytes: bytes) -> str:
        """
        Return an HMAC-SHA256 hex digest of `payload_bytes`
        using this webhook's secret.

        Header sent:  X-MailFlow-Signature: sha256=<hex>
        """
        sig = hmac.new(
            self.secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        )
        return f"sha256={sig.hexdigest()}"

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create_for_user(
        cls,
        user,
        *,
        label: str,
        url: str,
        event_types: list | None = None,
    ) -> "Webhook":
        return cls.objects.create(
            user=user,
            label=label,
            url=url,
            event_types=event_types or [],
        )


class WebhookDelivery(UUIDModel):
    """
    Immutable log of a single webhook delivery attempt.
    One row per attempt (retries create new rows).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED  = "failed",  "Failed"

    webhook     = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    event_type  = models.CharField(max_length=20)
    message_id  = models.UUIDField(null=True, blank=True)

    # Request
    payload     = models.JSONField(default=dict)
    attempt_no  = models.PositiveSmallIntegerField(default=1)

    # Response
    status      = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    attempted_at = models.DateTimeField(default=timezone.now, db_index=True)
    duration_ms  = models.PositiveIntegerField(
        null=True, blank=True, help_text="Round-trip time in milliseconds"
    )

    class Meta:
        verbose_name        = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"
        ordering            = ["-attempted_at"]
        indexes             = [
            models.Index(fields=["webhook", "status"]),
            models.Index(fields=["webhook", "attempted_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.status}] {self.event_type} → "
            f"{self.webhook.url[:40]} (attempt #{self.attempt_no})"
        )

    def mark_success(self, http_status: int, body: str, duration_ms: int) -> None:
        self.status       = self.Status.SUCCESS
        self.http_status  = http_status
        self.response_body = body[:2000]
        self.duration_ms  = duration_ms
        self.save(update_fields=[
            "status", "http_status", "response_body", "duration_ms"
        ])
        # Update webhook aggregate counters
        Webhook.objects.filter(pk=self.webhook_id).update(
            total_deliveries=models.F("total_deliveries") + 1,
            last_triggered=timezone.now(),
        )

    def mark_failed(self, error: str, http_status: int | None = None,
                    duration_ms: int | None = None) -> None:
        self.status        = self.Status.FAILED
        self.error_message = error[:2000]
        self.http_status   = http_status
        self.duration_ms   = duration_ms
        self.save(update_fields=[
            "status", "error_message", "http_status", "duration_ms"
        ])
        Webhook.objects.filter(pk=self.webhook_id).update(
            total_deliveries=models.F("total_deliveries") + 1,
            failed_deliveries=models.F("failed_deliveries") + 1,
            last_triggered=timezone.now(),
        )