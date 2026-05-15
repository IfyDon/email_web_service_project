"""
Event models — every lifecycle event attached to a Message.

MessageEvent  – immutable per-occurrence event record.
ClickToken    – maps a short redirect token to its original URL.
OpenToken     – maps a pixel token to its message.

Place: apps/events/models.py
"""

import uuid
from django.db import models
from django.utils import timezone

from core.models.base import UUIDModel, TimeStampedModel


class MessageEvent(UUIDModel):
    """
    Immutable lifecycle event row — one per occurrence.
    Never updated after creation.
    """

    class EventType(models.TextChoices):
        QUEUED       = "queued",       "Queued"
        SENDING      = "sending",      "Sending"
        DELIVERED    = "delivered",    "Delivered"
        OPENED       = "opened",       "Opened"
        CLICKED      = "clicked",      "Clicked"
        BOUNCED      = "bounced",      "Bounced"
        COMPLAINED   = "complained",   "Complained"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
        FAILED       = "failed",       "Failed"

    message     = models.ForeignKey(
        "email_messages.Message",
        on_delete=models.CASCADE,
        related_name="events",
        db_index=True,
    )
    event_type  = models.CharField(
        max_length=15, choices=EventType.choices, db_index=True
    )
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    # Engagement metadata
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True)
    location    = models.CharField(max_length=255, blank=True)

    # Populated for CLICKED events
    clicked_url = models.TextField(blank=True)

    # Raw ESP webhook payload for BOUNCED / COMPLAINED events
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name        = "Message Event"
        verbose_name_plural = "Message Events"
        ordering            = ["occurred_at"]
        indexes             = [
            models.Index(fields=["message", "event_type"]),
            models.Index(fields=["message", "occurred_at"]),
            models.Index(fields=["event_type", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.event_type} @ {self.occurred_at:%Y-%m-%d %H:%M} "
            f"for msg {self.message_id}"
        )

    @classmethod
    def record(
        cls,
        message,
        event_type: str,
        *,
        ip_address:  str | None = None,
        user_agent:  str = "",
        location:    str = "",
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


# ── Click tracking ────────────────────────────────────────────────────────────

class ClickToken(UUIDModel):
    """
    Persisted mapping: short URL-safe token → original link URL.

    One row per unique URL per message (reuse if the same URL
    appears multiple times in the same email body).
    """

    message      = models.ForeignKey(
        "email_messages.Message",
        on_delete=models.CASCADE,
        related_name="click_tokens",
    )
    token        = models.CharField(max_length=128, unique=True, db_index=True)
    original_url = models.TextField()

    # Engagement counters
    click_count  = models.PositiveIntegerField(default=0)
    first_clicked = models.DateTimeField(null=True, blank=True)
    last_clicked  = models.DateTimeField(null=True, blank=True)

    created_at   = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Click Token"
        ordering     = ["-created_at"]
        indexes      = [models.Index(fields=["token"])]

    def __str__(self) -> str:
        return f"ClickToken({self.token[:12]}…) → {self.original_url[:60]}"

    def record_click(self, ip: str = "", ua: str = "") -> "MessageEvent":
        """
        Increment counter, update timestamps, update message status,
        and persist a CLICKED MessageEvent.
        """
        now = timezone.now()
        self.click_count += 1
        if not self.first_clicked:
            self.first_clicked = now
        self.last_clicked = now
        self.save(update_fields=["click_count", "first_clicked", "last_clicked"])

        # Escalate message status (clicked > opened > delivered)
        msg = self.message
        if msg.status not in (
            msg.Status.BOUNCED,
            msg.Status.COMPLAINED,
            msg.Status.FAILED,
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


# ── Open tracking ─────────────────────────────────────────────────────────────

class OpenToken(UUIDModel):
    """
    Persisted mapping: short URL-safe token → message open pixel.

    One row per message (multiple fires increment open_count).
    """

    message      = models.ForeignKey(
        "email_messages.Message",
        on_delete=models.CASCADE,
        related_name="open_tokens",
    )
    token        = models.CharField(max_length=128, unique=True, db_index=True)

    # Engagement counters
    open_count   = models.PositiveIntegerField(default=0)
    first_opened = models.DateTimeField(null=True, blank=True)
    last_opened  = models.DateTimeField(null=True, blank=True)

    created_at   = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Open Token"
        ordering     = ["-created_at"]
        indexes      = [models.Index(fields=["token"])]

    def __str__(self) -> str:
        return f"OpenToken({self.token[:12]}…) for msg {self.message_id}"

    def record_open(self, ip: str = "", ua: str = "") -> "MessageEvent":
        """
        Increment counter, update timestamps, update message status,
        and persist an OPENED MessageEvent.
        """
        now = timezone.now()
        self.open_count += 1
        if not self.first_opened:
            self.first_opened = now
        self.last_opened = now
        self.save(update_fields=["open_count", "first_opened", "last_opened"])

        # Only escalate if not already in a higher state
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