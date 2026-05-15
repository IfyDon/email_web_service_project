"""
Webhook service — business logic for outbound webhook management.

Responsibilities:
  - Enumerate active webhooks that subscribe to an event
  - Build and enqueue Celery delivery tasks
  - CRUD helpers for the API + dashboard

Place: services/webhook_service.py
"""

import logging

from django.utils import timezone

from apps.webhooks.models import Webhook

logger = logging.getLogger(__name__)


# ── Event dispatch ────────────────────────────────────────────────────────────

def dispatch_event(
    user,
    event_type: str,
    message,
    metadata: dict | None = None,
) -> int:
    """
    Find all active webhooks for `user` that subscribe to `event_type`
    and enqueue a Celery delivery task for each.

    Returns the number of webhooks enqueued.
    Called from tracking_service and process_events task.
    """
    webhooks = Webhook.objects.filter(user=user, is_active=True)
    enqueued = 0

    for webhook in webhooks:
        if not webhook.subscribes_to(event_type):
            continue
        _enqueue_delivery(
            webhook=webhook,
            event_type=event_type,
            message_id=str(message.pk) if message else None,
            metadata=metadata or {},
        )
        enqueued += 1

    if enqueued:
        logger.info(
            "dispatch_event: %d webhook(s) enqueued for event '%s' (user %s)",
            enqueued, event_type, user.email,
        )
    return enqueued


def _enqueue_delivery(
    webhook: Webhook,
    event_type: str,
    message_id: str | None,
    metadata: dict,
) -> None:
    """Build the payload and push a delivery task onto the webhooks queue."""
    from workers.tasks.webhook_dispatch import deliver_webhook

    payload = _build_payload(
        event_type=event_type,
        message_id=message_id,
        metadata=metadata,
        webhook_id=str(webhook.pk),
    )

    deliver_webhook.apply_async(
        kwargs={
            "webhook_id": str(webhook.pk),
            "payload":    payload,
            "event_type": event_type,
            "message_id": message_id,
        },
        queue="webhooks",
    )


def _build_payload(
    event_type: str,
    message_id: str | None,
    metadata: dict,
    webhook_id: str,
) -> dict:
    """Standard payload shape sent to every webhook endpoint."""
    return {
        "event":      event_type,
        "message_id": message_id,
        "webhook_id": webhook_id,
        "occurred_at": timezone.now().isoformat(),
        "data":       metadata,
    }


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def create_webhook(user, *, label: str, url: str,
                   event_types: list | None = None) -> Webhook:
    return Webhook.create_for_user(
        user, label=label, url=url, event_types=event_types or []
    )


def update_webhook(
    webhook: Webhook,
    *,
    label: str | None = None,
    url: str | None = None,
    event_types: list | None = None,
    is_active: bool | None = None,
) -> Webhook:
    if label       is not None: webhook.label       = label
    if url         is not None: webhook.url         = url
    if event_types is not None: webhook.event_types = event_types
    if is_active   is not None: webhook.is_active   = is_active
    webhook.save()
    return webhook


def delete_webhook(webhook: Webhook) -> None:
    webhook.delete()


def test_webhook(webhook: Webhook) -> dict:
    """
    Send a test ping payload to the webhook URL immediately
    (synchronous, called from the dashboard test button).
    Returns {"success": bool, "http_status": int, "error": str}.
    """
    import json, time, requests

    payload = _build_payload(
        event_type="test",
        message_id=None,
        metadata={"note": "This is a test delivery from MailFlow."},
        webhook_id=str(webhook.pk),
    )
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature     = webhook.sign_payload(payload_bytes)

    start = time.monotonic()
    try:
        resp = requests.post(
            webhook.url,
            data=payload_bytes,
            headers={
                "Content-Type":        "application/json",
                "X-MailFlow-Event":    "test",
                "X-MailFlow-Signature": signature,
            },
            timeout=10,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        success     = 200 <= resp.status_code < 300
        return {
            "success":     success,
            "http_status": resp.status_code,
            "body":        resp.text[:500],
            "duration_ms": duration_ms,
            "error":       "" if success else f"HTTP {resp.status_code}",
        }
    except requests.RequestException as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        return {
            "success":     False,
            "http_status": None,
            "body":        "",
            "duration_ms": duration_ms,
            "error":       str(exc),
        }