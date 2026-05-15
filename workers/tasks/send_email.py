"""
Celery task: dispatch_send_task
───────────────────────────────
Picks up a queued Message, builds the MIME payload, sends via the
configured ESP (SES or SMTP), and records the attempt result.

Retry strategy: exponential back-off up to message.max_attempts.
  Delay schedule (seconds): 5, 25, 125, 625, 3125

Place: workers/tasks/send_email.py
"""

import logging
from celery import shared_task
from django.utils import timezone

from apps.email_messages.models import Message, MessageAttempt
from services.suppression_service import (
    generate_unsubscribe_token,
    build_list_unsubscribe_header,
)

logger = logging.getLogger(__name__)

# ── ESP router ────────────────────────────────────────────────────────────────

def _get_esp_client():
    """
    Return the active ESP send function based on settings.
    Defaults to SMTP so local dev works without AWS credentials.
    """
    from django.conf import settings
    backend = getattr(settings, "EMAIL_DISPATCH_BACKEND", "smtp")

    if backend == "ses":
        from integrations.ses.client import send_email
        return send_email
    else:
        from integrations.smtp.client import send_email
        return send_email


# ── Main task ─────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="workers.tasks.send_email.dispatch_send_task",
    max_retries=5,
    default_retry_delay=5,        # overridden per-attempt below
    acks_late=True,               # only ack after successful processing
    reject_on_worker_lost=True,
)
def dispatch_send_task(
    self,
    message_id: str,
    *,
    track_opens: bool = True,
    track_clicks: bool = True,
) -> dict:
    """
    Load a queued Message, send it, and record the attempt.

    Returns a summary dict for Celery result storage.
    On transient failure: schedules exponential-backoff retry.
    On permanent failure (retries exhausted): marks message as FAILED.
    """
    # ── Load message ──────────────────────────────────────────────────────────
    try:
        message = (
            Message.objects
            .select_related("user", "domain")
            .get(pk=message_id)
        )
    except Message.DoesNotExist:
        logger.error("dispatch_send_task: Message %s not found.", message_id)
        return {"status": "not_found", "message_id": message_id}

    # Guard: skip if already terminal
    if message.is_terminal:
        logger.info(
            "dispatch_send_task: Message %s already in terminal state '%s'.",
            message_id, message.status,
        )
        return {"status": "skipped", "message_id": message_id}

    # ── Build extra headers ───────────────────────────────────────────────────
    extra_headers = _build_headers(message, track_opens)

    # ── Rewrite links for click tracking (Phase 3.3) ──────────────────────────
    body_html = message.body_html
    body_text = message.body_text
    if track_clicks and body_html:
        from services.tracking_service import rewrite_links
        body_html = rewrite_links(body_html, message)

    # ── Insert open-tracking pixel (Phase 3.3) ────────────────────────────────
    if track_opens and body_html:
        from services.tracking_service import inject_tracking_pixel
        body_html = inject_tracking_pixel(body_html, message)

    # ── Mark as sending ───────────────────────────────────────────────────────
    message.mark_sending()

    # ── Dispatch to ESP ───────────────────────────────────────────────────────
    attempt_no = message.attempt_count
    esp_send   = _get_esp_client()
    esp_response = {}

    try:
        esp_message_id = esp_send(
            from_email=message.from_email,
            from_name=message.from_name,
            to_email=message.to_email,
            to_name=message.to_name,
            subject=message.subject,
            body_html=body_html,
            body_text=body_text,
            reply_to=message.reply_to,
            headers=extra_headers,
        )
        esp_response = {"message_id": esp_message_id}

        # ── Record success ────────────────────────────────────────────────────
        MessageAttempt.objects.create(
            message=message,
            attempt_no=attempt_no,
            success=True,
            esp_response=esp_response,
            attempted_at=timezone.now(),
        )
        message.mark_sent(esp_message_id=esp_message_id)

        logger.info(
            "Message %s sent successfully via ESP (attempt #%d, esp_id=%s).",
            message_id, attempt_no, esp_message_id,
        )
        return {
            "status":        "sent",
            "message_id":    message_id,
            "esp_message_id": esp_message_id,
            "attempt":       attempt_no,
        }

    except RuntimeError as exc:
        # ── Record failure ────────────────────────────────────────────────────
        MessageAttempt.objects.create(
            message=message,
            attempt_no=attempt_no,
            success=False,
            error=str(exc),
            esp_response=esp_response,
            attempted_at=timezone.now(),
        )

        if message.retries_exhausted:
            message.mark_failed(schedule_retry=False)
            logger.error(
                "Message %s permanently failed after %d attempts: %s",
                message_id, attempt_no, exc,
            )
            return {
                "status":     "failed",
                "message_id": message_id,
                "error":      str(exc),
            }

        # Exponential back-off: 5^attempt seconds
        import math
        delay = int(math.pow(5, attempt_no))
        message.mark_failed(schedule_retry=True)

        logger.warning(
            "Message %s failed (attempt #%d), retrying in %ds: %s",
            message_id, attempt_no, delay, exc,
        )
        raise self.retry(exc=exc, countdown=delay)


# ── Header builder ────────────────────────────────────────────────────────────

def _build_headers(message: Message, track_opens: bool) -> dict:
    """
    Assemble the extra email headers:
      - List-Unsubscribe (RFC 8058)
      - List-Unsubscribe-Post (one-click)
      - X-Mailer
      - X-MailFlow-Message-ID
    """
    from django.conf import settings
    base_url = getattr(settings, "APP_BASE_URL", "http://localhost:8000")

    # Generate a per-message unsubscribe token
    token = generate_unsubscribe_token(
        user=message.user,
        email=message.to_email,
        message_id=message.pk,
    )

    unsub_header = build_list_unsubscribe_header(token, base_url)

    return {
        "List-Unsubscribe":      unsub_header,
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        "X-Mailer":              "MailFlow/1.0",
        "X-MailFlow-Message-ID": str(message.pk),
    }