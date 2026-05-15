"""
Celery task: deliver_webhook
────────────────────────────
Sends a signed JSON POST to a user's webhook endpoint.

Retry strategy: exponential back-off, up to 5 attempts.
  Delays (seconds): 30, 150, 750, 3 750, 18 750

Dead-letter behaviour: after max retries the WebhookDelivery row
is left in status=failed for the user to inspect in the dashboard.

Place: workers/tasks/webhook_dispatch.py
"""

import json
import logging
import math
import time

import requests
from celery import shared_task
from django.utils import timezone

from apps.webhooks.models import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_CONNECT_TIMEOUT = 5   # seconds — connection establishment
_READ_TIMEOUT    = 10  # seconds — waiting for response body
_MAX_RETRIES     = 5
_BASE_DELAY      = 30  # seconds for first retry; multiplied by 5^attempt


@shared_task(
    bind=True,
    name="workers.tasks.webhook_dispatch.deliver_webhook",
    max_retries=_MAX_RETRIES,
    acks_late=True,
    reject_on_worker_lost=True,
    queue="webhooks",
)
def deliver_webhook(
    self,
    *,
    webhook_id: str,
    payload: dict,
    event_type: str,
    message_id: str | None = None,
    attempt_no: int = 1,
) -> dict:
    """
    HTTP POST `payload` to the webhook's configured URL.

    On 2xx → mark delivery SUCCESS.
    On non-2xx / network error → retry with exponential back-off.
    On retries exhausted → mark FAILED (dead-letter).
    """
    # ── Load webhook ──────────────────────────────────────────────────────────
    try:
        webhook = Webhook.objects.get(pk=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        logger.warning("deliver_webhook: Webhook %s not found or inactive.", webhook_id)
        return {"status": "skipped", "reason": "webhook_not_found"}

    # ── Create delivery log row ───────────────────────────────────────────────
    delivery = WebhookDelivery.objects.create(
        webhook=webhook,
        event_type=event_type,
        message_id=message_id,
        payload=payload,
        attempt_no=attempt_no,
    )

    # ── Build request ─────────────────────────────────────────────────────────
    payload_bytes = json.dumps(payload, default=str).encode("utf-8")
    signature     = webhook.sign_payload(payload_bytes)

    headers = {
        "Content-Type":          "application/json",
        "User-Agent":            "MailFlow-Webhooks/1.0",
        "X-MailFlow-Event":      event_type,
        "X-MailFlow-Signature":  signature,
        "X-MailFlow-Delivery-ID": str(delivery.pk),
        "X-MailFlow-Attempt":    str(attempt_no),
    }

    # ── Send ──────────────────────────────────────────────────────────────────
    start = time.monotonic()
    try:
        resp = requests.post(
            webhook.url,
            data=payload_bytes,
            headers=headers,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        if 200 <= resp.status_code < 300:
            delivery.mark_success(
                http_status=resp.status_code,
                body=resp.text,
                duration_ms=duration_ms,
            )
            logger.info(
                "Webhook %s delivered (event=%s, http=%d, attempt=%d, %dms)",
                webhook_id, event_type, resp.status_code, attempt_no, duration_ms,
            )
            return {
                "status":      "success",
                "http_status": resp.status_code,
                "attempt":     attempt_no,
                "duration_ms": duration_ms,
            }

        # Non-2xx: treat as failure, retry
        error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
        delivery.mark_failed(
            error=error_msg,
            http_status=resp.status_code,
            duration_ms=duration_ms,
        )
        logger.warning(
            "Webhook %s non-2xx (event=%s, http=%d, attempt=%d): %s",
            webhook_id, event_type, resp.status_code, attempt_no, error_msg,
        )
        raise _RetryableError(error_msg)

    except requests.Timeout:
        duration_ms = int((time.monotonic() - start) * 1000)
        error_msg   = f"Request timed out after {duration_ms}ms"
        delivery.mark_failed(error=error_msg, duration_ms=duration_ms)
        logger.warning("Webhook %s timed out (attempt=%d)", webhook_id, attempt_no)
        raise _RetryableError(error_msg)

    except requests.ConnectionError as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        error_msg   = f"Connection error: {exc}"
        delivery.mark_failed(error=error_msg, duration_ms=duration_ms)
        logger.warning("Webhook %s connection error (attempt=%d): %s",
                       webhook_id, attempt_no, exc)
        raise _RetryableError(error_msg)

    except _RetryableError as exc:
        # ── Schedule retry or give up ─────────────────────────────────────────
        next_attempt = attempt_no + 1
        if attempt_no >= _MAX_RETRIES:
            logger.error(
                "Webhook %s permanently failed after %d attempts (event=%s).",
                webhook_id, attempt_no, event_type,
            )
            return {
                "status":  "dead_letter",
                "webhook": webhook_id,
                "event":   event_type,
                "error":   str(exc),
            }

        delay = int(math.pow(5, attempt_no)) * _BASE_DELAY // 5
        logger.info(
            "Webhook %s retry #%d in %ds (event=%s)",
            webhook_id, next_attempt, delay, event_type,
        )
        raise self.retry(
            exc=exc,
            countdown=delay,
            kwargs={
                "webhook_id":  webhook_id,
                "payload":     payload,
                "event_type":  event_type,
                "message_id":  message_id,
                "attempt_no":  next_attempt,
            },
        )


class _RetryableError(Exception):
    """Internal sentinel — triggers Celery retry from the except block."""