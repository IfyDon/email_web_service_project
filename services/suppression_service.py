"""
Suppression service — business logic for suppression list management.

Responsibilities:
  - Pre-send check (block suppressed addresses)
  - Adding suppressions from ESP bounce/complaint webhooks
  - Generating unsubscribe tokens + List-Unsubscribe headers
  - CAN-SPAM / GDPR compliance helpers

Place: services/suppression_service.py
"""

import logging
from typing import Iterable

from django.conf import settings

from apps.suppressions.models import Suppression, UnsubscribeToken
from core.exceptions import RecipientSuppressed

logger = logging.getLogger(__name__)


# ── Pre-send guard ────────────────────────────────────────────────────────────

def check_recipients(user, emails: Iterable[str]) -> list[str]:
    """
    Filter out suppressed addresses from a list of recipients.

    Returns the clean (allowed) list.
    Logs each suppressed address; if ALL addresses are suppressed, raises
    RecipientSuppressed so the caller can return a useful API error.
    """
    emails     = [e.lower().strip() for e in emails if e]
    suppressed = []
    allowed    = []

    for email in emails:
        if Suppression.is_suppressed(user, email):
            suppressed.append(email)
            logger.info("Suppressed address blocked: %s (user %s)", email, user.email)
        else:
            allowed.append(email)

    if suppressed and not allowed:
        raise RecipientSuppressed(
            f"All recipients are suppressed: {', '.join(suppressed)}"
        )

    return allowed


# ── Add from ESP events ───────────────────────────────────────────────────────

def record_bounce(user, email: str, message_id=None) -> Suppression:
    """
    Add a hard-bounce suppression.
    Called by the ESP webhook handler (Phase 3).
    """
    sup = Suppression.suppress(
        user=user,
        email=email,
        reason=Suppression.Reason.BOUNCE,
        source_message_id=message_id,
    )
    logger.info("Bounce suppression added: %s", email)
    return sup


def record_complaint(user, email: str, message_id=None) -> Suppression:
    """
    Add a spam-complaint suppression.
    Called by the ESP webhook handler (Phase 3).
    """
    sup = Suppression.suppress(
        user=user,
        email=email,
        reason=Suppression.Reason.COMPLAINT,
        source_message_id=message_id,
    )
    logger.info("Complaint suppression added: %s", email)
    return sup


def record_unsubscribe(user, email: str, message_id=None) -> Suppression:
    """
    Add an unsubscribe suppression (e.g. from one-click List-Unsubscribe POST).
    """
    sup = Suppression.suppress(
        user=user,
        email=email,
        reason=Suppression.Reason.UNSUBSCRIBE,
        source_message_id=message_id,
    )
    logger.info("Unsubscribe suppression added: %s", email)
    return sup


def add_manual(user, email: str, description: str = "") -> Suppression:
    """Manually suppress an address from the dashboard."""
    return Suppression.suppress(
        user=user,
        email=email,
        reason=Suppression.Reason.MANUAL,
        description=description,
    )


def remove_suppression(user, email: str) -> bool:
    """
    Remove a suppression (allow sending again).
    Returns True if a record was found and deleted.
    """
    removed = Suppression.remove(user, email)
    if removed:
        logger.info("Suppression removed for %s by %s", email, user.email)
    return removed


# ── Unsubscribe token helpers ─────────────────────────────────────────────────

def generate_unsubscribe_token(user, email: str, message_id=None) -> UnsubscribeToken:
    """
    Create a fresh unsubscribe token for an outgoing message.
    Called by email_service before dispatch (Phase 3).
    """
    return UnsubscribeToken.create(user=user, email=email, message_id=message_id)


def build_list_unsubscribe_header(token: UnsubscribeToken, base_url: str) -> str:
    """
    Build the RFC-8058 List-Unsubscribe header value.

    Returns a string like:
      <https://app.mailflow.io/unsubscribe/abc123/>,
      <mailto:unsub@mailflow.io?subject=unsubscribe>
    """
    unsub_url   = f"{base_url}/unsubscribe/{token.token}/"
    mailto_part = f"<mailto:{settings.DEFAULT_FROM_EMAIL}?subject=unsubscribe>"
    return f"<{unsub_url}>, {mailto_part}"


def consume_unsubscribe_token(raw_token: str) -> tuple[bool, str | None]:
    """
    Find and consume a raw unsubscribe token.

    Returns:
        (success: bool, email: str | None)
    """
    try:
        token = UnsubscribeToken.objects.select_related("user").get(token=raw_token)
    except UnsubscribeToken.DoesNotExist:
        logger.warning("Unknown unsubscribe token: %s", raw_token)
        return False, None

    if token.used:
        return False, token.email   # Already processed – idempotent success

    ok = token.consume()
    return ok, token.email


# ── List helpers ──────────────────────────────────────────────────────────────

def get_suppressions(user, reason: str | None = None):
    """Return QS of suppressions for a user, optionally filtered by reason."""
    qs = Suppression.objects.filter(user=user)
    if reason:
        qs = qs.filter(reason=reason)
    return qs.order_by("-created_at")