"""
Celery tasks for processing inbound ESP webhook events.

dispatch_esp_event  – fan-out router called by the webhook receiver view
_handle_delivered   – mark message delivered
_handle_bounce      – mark bounced + suppress address
_handle_complaint   – mark complained + suppress address
_handle_open        – mark opened (via ESP beacon, not our pixel)
_handle_click       – mark clicked (via ESP link wrapping, not our redirect)

Place: workers/tasks/process_events.py
"""

import logging
from celery import shared_task
from django.utils import timezone

from apps.email_messages.models import Message
from apps.events.models import MessageEvent

logger = logging.getLogger(__name__)


@shared_task(
    name="workers.tasks.process_events.dispatch_esp_event",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def dispatch_esp_event(self, payload: dict) -> dict:
    """
    Route an inbound ESP webhook event to the correct handler.

    Expected payload shape (normalised by the webhook receiver):
    {
        "event":       "delivered" | "bounced" | "complained" | "opened" | "clicked",
        "esp_message_id": "<ESP's message id>",
        "to_email":    "user@example.com",
        "occurred_at": "<ISO-8601>",   # optional
        "metadata":    {}              # raw ESP payload
    }
    """
    event_type    = payload.get("event", "")
    esp_msg_id    = payload.get("esp_message_id", "")
    to_email      = payload.get("to_email", "")
    raw_payload   = payload.get("metadata", {})
    occurred_at   = payload.get("occurred_at")

    try:
        message = Message.objects.get(esp_message_id=esp_msg_id)
    except Message.DoesNotExist:
        logger.warning(
            "dispatch_esp_event: no Message found for esp_message_id=%s", esp_msg_id
        )
        return {"status": "not_found", "esp_message_id": esp_msg_id}
    except Message.MultipleObjectsReturned:
        logger.error(
            "dispatch_esp_event: multiple Messages for esp_message_id=%s", esp_msg_id
        )
        return {"status": "ambiguous", "esp_message_id": esp_msg_id}

    handlers = {
        "delivered":  _handle_delivered,
        "bounced":    _handle_bounce,
        "complained": _handle_complaint,
        "opened":     _handle_open,
        "clicked":    _handle_click,
    }

    handler = handlers.get(event_type)
    if not handler:
        logger.warning("dispatch_esp_event: unknown event type '%s'", event_type)
        return {"status": "unknown_event", "event": event_type}

    try:
        handler(message, raw_payload=raw_payload, occurred_at=occurred_at)
        return {"status": "ok", "event": event_type, "message_id": str(message.pk)}
    except Exception as exc:
        logger.exception("dispatch_esp_event handler failed: %s", exc)
        raise self.retry(exc=exc)


# ── Event handlers ────────────────────────────────────────────────────────────

def _handle_delivered(message: Message, *, raw_payload: dict, occurred_at=None):
    if message.status not in (
        Message.Status.OPENED,
        Message.Status.CLICKED,
    ):
        message.status       = Message.Status.DELIVERED
        message.delivered_at = timezone.now()
        message.save(update_fields=["status", "delivered_at", "updated_at"])

    MessageEvent.record(
        message=message,
        event_type=MessageEvent.EventType.DELIVERED,
        raw_payload=raw_payload,
    )
    logger.info("Message %s delivered (ESP confirmation).", message.pk)


def _handle_bounce(message: Message, *, raw_payload: dict, occurred_at=None):
    message.mark_bounced()
    MessageEvent.record(
        message=message,
        event_type=MessageEvent.EventType.BOUNCED,
        raw_payload=raw_payload,
    )

    # Suppress the address
    from services.suppression_service import record_bounce
    record_bounce(
        user=message.user,
        email=message.to_email,
        message_id=message.pk,
    )
    logger.info("Message %s bounced — %s suppressed.", message.pk, message.to_email)


def _handle_complaint(message: Message, *, raw_payload: dict, occurred_at=None):
    message.mark_complained()
    MessageEvent.record(
        message=message,
        event_type=MessageEvent.EventType.COMPLAINED,
        raw_payload=raw_payload,
    )

    # Suppress the address
    from services.suppression_service import record_complaint
    record_complaint(
        user=message.user,
        email=message.to_email,
        message_id=message.pk,
    )
    logger.info("Message %s complaint — %s suppressed.", message.pk, message.to_email)


def _handle_open(message: Message, *, raw_payload: dict, occurred_at=None):
    """ESP-reported open (not from our pixel — no OpenToken involved)."""
    if message.status not in (
        Message.Status.CLICKED,
        Message.Status.BOUNCED,
        Message.Status.COMPLAINED,
        Message.Status.FAILED,
    ):
        message.status = Message.Status.OPENED
        message.save(update_fields=["status", "updated_at"])

    MessageEvent.record(
        message=message,
        event_type=MessageEvent.EventType.OPENED,
        raw_payload=raw_payload,
    )


def _handle_click(message: Message, *, raw_payload: dict, occurred_at=None):
    """ESP-reported click."""
    if message.status not in (
        Message.Status.BOUNCED,
        Message.Status.COMPLAINED,
        Message.Status.FAILED,
    ):
        message.status = Message.Status.CLICKED
        message.save(update_fields=["status", "updated_at"])

    MessageEvent.record(
        message=message,
        event_type=MessageEvent.EventType.CLICKED,
        clicked_url=raw_payload.get("url", ""),
        raw_payload=raw_payload,
    )