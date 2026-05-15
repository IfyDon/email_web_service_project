"""
Event models — every lifecycle event attached to a Message.

MessageEvent  – immutable record of delivered/opened/clicked/bounced/etc.
ClickToken    – stores the original URL behind each rewritten click link.

Place: apps/events/models.py
"""

import uuid
from django.db import models
from django.utils import timezone

from core.models.base import UUIDModel, TimeStampedModel


class MessageEvent(UUIDModel):
    """
    Immutable lifecycle event for an outgoing Message.

    One row per occurrence — a message may have many events
    (multiple opens, multiple clicks on different links, etc.).

    Event types mirror both ESP webhook payloads and our own
    open/click tracking endpoints.
    """

    class EventType(models.TextChoices):
        QUEUED     = "queued",      "Queued"
        SENDING    = "sending",     "Sending"
        DELIVERED  = "delivered",   "Delivered"
        OPENED     = "opened",      "Opened"
        CLICKED    = "clicked",     "Clicked"
        BOUNCED    = "bounced",     "Bounced"
        COMPLAINED = "complained",  "Complained"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
        FAILED     = "failed",      "Failed"

    # ── Relations ─────────────────────────────────────────────────────────────
    message    = models.ForeignKey(
        "email_messages.Message",
        on_delete=models.CASCADE,
        related_name="events",
        db_index=True,
    )

    # ── Event data ────────────────────────────────────────────────────────────
    event_type = models.CharField(
        max_length=15, choices=EventType.choices, db_index=True
    )
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Engagement metadata
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True)
    location    = models.CharField(max_length=255, blank=True)

    # For click events — the URL that was clicked
    clicked_url = models.TextField(blank=True)

    # ESP-supplied raw payload (bounce reason, feedback loop data, etc.)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name        = "Message Event"
        verbose_name_plural = "Message Events"
        ordering            = ["occurred_at"]
        indexes             = [
            models.Index(fields=["message", "event_type"]),
            models.Index(fields=["message", "occurred_at"]),
            # For analytics aggregations by type + time
            models.Index(fields=["event_type", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.occurred_at:%Y-%m-%d %H:%M} for msg {self.message_id}"

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def record(
        cls,
        message,
        event_type: str,
        *,
        ip_address: str | None = None,
        user_agent: str = "",
        location:   str = "",
        clicked_url: str = "",
        raw_payload: dict | None = None,
        occurred_at=None,
    ) -> "MessageEvent":
        return cls.objects.create(
            message=message,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            location=location,
            clicked_url=clicked_url,
            raw_payload=raw_payload or {},
            occurred_at=occurred_at or timezone.now(),
        )


class ClickToken(UUIDModel):
    """
    Maps a short click-tracking token to its original URL.

    Created by tracking_service.rewrite_links() when building
    outgoing email HTML. Looked up by tracking/views.py on redirect.
    """

    message      = models.ForeignKey(
        "email_messages.Message",
        on_delete=models.CASCADE,
        related_name="click_tokens",
    )
    token        = models.CharField(max_length=128, unique=True, db_index=True)
    original_url = models.TextField()
    click_count  = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(default=timezone.now)
    last_clicked = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Click Token"
        ordering     = ["-created_at"]

    def __str__(self) -> str:
        return f"ClickToken({self.token[:12]}…) → {self.original_url[:60]}"

    def record_click(self, ip: str = "", ua: str = "") -> MessageEvent:
        """Increment counter, update last_clicked, and record a CLICKED event."""
        self.click_count += 1
        self.last_clicked = timezone.now()
        self.save(update_fields=["click_count", "last_clicked"])

        # Update parent message status to CLICKED (highest engagement)
        msg = self.message
        if msg.status not in (
            msg.Status.BOUNCED, msg.Status.COMPLAINED, msg.Status.FAILED
        ):
            msg.status = msg.Status.CLICKED
            msg.save(update_fields=["status", "updated_at"])

        return MessageEvent.record(
            message=msg,
            event_type=MessageEvent.EventType.CLICKED,
            ip_address=ip or None,
            user_agent=ua,
            clicked_url=self.original_url,
        )


class OpenToken(UUIDModel):
    """
    Maps a short open-tracking token to its message.

    Created by tracking_service.inject_tracking_pixel().
    Looked up by tracking/views.py when the pixel fires.
    """

    message     = models.ForeignKey(
        "email_messages.Message",
        on_delete=models.CASCADE,
        related_name="open_tokens",
    )
    token       = models.CharField(max_length=128, unique=True, db_index=True)
    open_count  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(default=timezone.now)
    first_opened = models.DateTimeField(null=True, blank=True)
    last_opened  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Open Token"
        ordering     = ["-created_at"]

    def __str__(self) -> str:
        return f"OpenToken({self.token[:12]}…) for msg {self.message_id}"

    def record_open(self, ip: str = "", ua: str = "") -> MessageEvent:
        """Increment counter and record an OPENED event."""
        now = timezone.now()
        self.open_count += 1
        if not self.first_opened:
            self.first_opened = now
        self.last_opened = now
        self.save(update_fields=["open_count", "first_opened", "last_opened"])

        # Update parent message status
        msg = self.message
        if msg.status not in (
            msg.Status.CLICKED,
            msg.Status.BOUNCED,
            msg.Status.COMPLAINED,
            msg.Status.FAILED,
        ):
            msg.status = msg.Status.OPENED
            msg.save(update_fields=["status", "updated_at"])

        return MessageEvent.record(
            message=msg,
            event_type=MessageEvent.EventType.OPENED,
            ip_address=ip or None,
            user_agent=ua,
        )