"""
Email service — the single entry point for all outgoing email.

Responsibilities:
  - Validate payload (quota, suppression, domain ownership)
  - Persist a Message record with status=queued
  - Enqueue a Celery send task and return immediately
  - Support single send and bulk send (fan-out)

Place: services/email_service.py
"""

import logging
import uuid
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from apps.email_messages.models import Message
from apps.domains.models import Domain
from apps.templates_app.models import EmailTemplate
from services.suppression_service import (
    check_recipients,
    generate_unsubscribe_token,
    build_list_unsubscribe_header,
)
from services.template_service import render_template
from core.exceptions import (
    QuotaExceeded,
    DomainNotVerified,
    RecipientSuppressed,
    TemplateRenderError,
)

logger = logging.getLogger(__name__)

# Base URL used in List-Unsubscribe headers — override in settings
_BASE_URL = getattr(settings, "APP_BASE_URL", "http://localhost:8000")


# ── Public API ────────────────────────────────────────────────────────────────

def send_single(
    user,
    *,
    to_email: str,
    subject: str,
    from_email: str | None = None,
    from_name: str = "",
    to_name: str = "",
    reply_to: str = "",
    body_html: str = "",
    body_text: str = "",
    template_id: str | None = None,
    template_context: dict | None = None,
    domain_id: str | None = None,
    tags: list | None = None,
    metadata: dict | None = None,
    track_opens: bool = True,
    track_clicks: bool = True,
) -> Message:
    """
    Validate, persist and queue a single outgoing email.

    Returns the Message (status=queued) immediately.
    Actual sending happens asynchronously in a Celery worker.

    Raises:
        QuotaExceeded        – user's monthly sending limit reached
        DomainNotVerified    – from_email domain not verified
        RecipientSuppressed  – to_email is suppressed
        TemplateRenderError  – template substitution failed
    """
    # ── 1. Quota guard ────────────────────────────────────────────────────────
    if user.quota_exceeded:
        raise QuotaExceeded()

    # ── 2. Suppression check ──────────────────────────────────────────────────
    allowed = check_recipients(user, [to_email])   # raises if suppressed
    to_email = allowed[0]

    # ── 3. Resolve sending domain ─────────────────────────────────────────────
    domain = _resolve_domain(user, from_email, domain_id)
    from_email = from_email or f"noreply@{domain.name}"

    # ── 4. Resolve / render template ──────────────────────────────────────────
    if template_id:
        subject, body_html, body_text = _render_from_template(
            user, template_id, template_context or {}
        )

    if not body_html and not body_text:
        raise ValueError("At least one of body_html or body_text is required.")

    # ── 5. Persist Message (status=queued) ────────────────────────────────────
    message = Message.objects.create(
        user=user,
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        to_name=to_name,
        reply_to=reply_to,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        domain=domain,
        template_id=template_id,
        tags=tags or [],
        metadata=metadata or {},
        status=Message.Status.QUEUED,
        queued_at=timezone.now(),
    )

    # ── 6. Enqueue Celery task ────────────────────────────────────────────────
    _enqueue(message, track_opens=track_opens, track_clicks=track_clicks)

    logger.info("Message %s queued for %s", message.pk, to_email)
    return message


def send_bulk(
    user,
    *,
    recipients: list[dict],
    subject: str | None = None,
    from_email: str | None = None,
    from_name: str = "",
    body_html: str = "",
    body_text: str = "",
    template_id: str | None = None,
    domain_id: str | None = None,
    tags: list | None = None,
    track_opens: bool = True,
    track_clicks: bool = True,
) -> list[Message]:
    """
    Fan-out a bulk send: each recipient dict may carry its own context.

    recipients = [
        {"to_email": "a@x.com", "to_name": "Alice",
         "context": {"first_name": "Alice"}},
        ...
    ]

    Checks quota for the entire batch upfront, then fans out individual
    send_single() calls (which each enqueue their own Celery task).

    Returns the list of queued Message objects.
    Chunks are capped at 1 000 per call (enforced at the API layer too).
    """
    if len(recipients) > 1000:
        raise ValueError("Bulk send is limited to 1 000 recipients per call.")

    # Upfront quota check for the entire batch
    if user.emails_sent_mtd + len(recipients) > user.monthly_quota:
        raise QuotaExceeded(
            f"Batch of {len(recipients)} would exceed monthly quota "
            f"({user.quota_remaining} remaining)."
        )

    messages = []
    for rec in recipients:
        try:
            msg = send_single(
                user,
                to_email=rec["to_email"],
                to_name=rec.get("to_name", ""),
                subject=rec.get("subject", subject or ""),
                from_email=from_email,
                from_name=from_name,
                body_html=rec.get("body_html", body_html),
                body_text=rec.get("body_text", body_text),
                template_id=template_id,
                template_context=rec.get("context", {}),
                domain_id=domain_id,
                tags=tags,
                track_opens=track_opens,
                track_clicks=track_clicks,
            )
            messages.append(msg)
        except (RecipientSuppressed, TemplateRenderError) as exc:
            # Log per-recipient errors but continue the batch
            logger.warning(
                "Skipping %s in bulk send: %s", rec.get("to_email"), exc
            )

    logger.info(
        "Bulk send: %d queued, %d skipped out of %d recipients",
        len(messages), len(recipients) - len(messages), len(recipients),
    )
    return messages


# ── Internal helpers ──────────────────────────────────────────────────────────

def _resolve_domain(user, from_email: str | None, domain_id: str | None) -> Domain:
    """
    Find the verified Domain to use for sending.

    Priority:
      1. Explicit domain_id param
      2. Domain extracted from from_email
      3. First verified domain owned by user
    Raises DomainNotVerified if none found.
    """
    if domain_id:
        try:
            domain = Domain.objects.get(pk=domain_id, user=user)
            if not domain.is_verified:
                raise DomainNotVerified(
                    f"Domain '{domain.name}' is not fully verified."
                )
            return domain
        except Domain.DoesNotExist:
            raise DomainNotVerified("Specified domain not found.")

    if from_email:
        domain_name = from_email.split("@")[-1].lower()
        try:
            domain = Domain.objects.get(name=domain_name, user=user)
            if not domain.is_verified:
                raise DomainNotVerified(
                    f"Domain '{domain_name}' is registered but not yet verified."
                )
            return domain
        except Domain.DoesNotExist:
            raise DomainNotVerified(
                f"Domain '{domain_name}' is not registered on your account."
            )

    # Fall back to first verified domain
    domain = Domain.objects.filter(user=user, status=Domain.Status.VERIFIED).first()
    if not domain:
        raise DomainNotVerified(
            "No verified sending domain found. "
            "Add and verify a domain before sending."
        )
    return domain


def _render_from_template(
    user, template_id: str, context: dict
) -> tuple[str, str, str]:
    """
    Load template by id and render subject + bodies.
    Returns (subject, body_html, body_text).
    """
    try:
        template = EmailTemplate.objects.get(pk=template_id, user=user, is_active=True)
    except EmailTemplate.DoesNotExist:
        raise TemplateRenderError(
            f"Template '{template_id}' not found or inactive."
        )
    rendered = render_template(template, context)
    return rendered["subject"], rendered["body_html"], rendered["body_text"]


def _enqueue(message: Message, *, track_opens: bool, track_clicks: bool) -> None:
    """
    Dispatch the Celery send task.
    Stores the task id back on the message for status lookup.
    """
    from workers.tasks.send_email import dispatch_send_task

    task = dispatch_send_task.apply_async(
        args=[str(message.pk)],
        kwargs={"track_opens": track_opens, "track_clicks": track_clicks},
        # Celery will retry up to message.max_attempts via the task itself
        countdown=0,
    )
    # Store celery task id for monitoring
    Message.objects.filter(pk=message.pk).update(celery_task_id=task.id)