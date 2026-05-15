"""
Tracking service — open pixel injection and click link rewriting.

Replaces the Phase 3.1 stubs with fully DB-backed, signed tokens.

Responsibilities:
  - Generate + persist OpenToken / ClickToken rows
  - Inject 1×1 tracking pixel before </body>
  - Rewrite all href= links to the click-redirect endpoint
  - Decode incoming tokens for the tracking views
  - Record open / click events on the Message

Place: services/tracking_service.py
"""

import hashlib
import logging
import re
import secrets

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_BASE_URL = getattr(settings, "APP_BASE_URL", "http://localhost:8000")

# Matches http(s) hrefs, skips mailto / unsubscribe links
_HREF_RE = re.compile(
    r'href="(https?://(?!(?:localhost|127\.0\.0\.1))[^"]+)"',
    re.IGNORECASE,
)


# ── Token generation ──────────────────────────────────────────────────────────

def _make_token() -> str:
    """64-char URL-safe random token."""
    return secrets.token_urlsafe(48)


# ── Open pixel ────────────────────────────────────────────────────────────────

def create_open_token(message) -> "OpenToken":
    """Create and persist an OpenToken for `message`."""
    from apps.events.models import OpenToken
    return OpenToken.objects.create(
        message=message,
        token=_make_token(),
    )


def inject_tracking_pixel(body_html: str, message) -> str:
    """
    Insert a 1×1 transparent GIF pixel just before </body>.
    Creates a persistent OpenToken row so the pixel URL can be resolved.
    """
    token_obj = create_open_token(message)
    pixel_url = f"{_BASE_URL}/t/o/{token_obj.token}/"
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'alt="" style="display:none;border:none;width:1px;height:1px;" />'
    )

    if "</body>" in body_html:
        return body_html.replace("</body>", f"{pixel_tag}</body>", 1)
    return body_html + pixel_tag


# ── Click tracking ────────────────────────────────────────────────────────────

def create_click_token(message, original_url: str) -> "ClickToken":
    """Create and persist a ClickToken for one rewritten URL."""
    from apps.events.models import ClickToken
    return ClickToken.objects.create(
        message=message,
        token=_make_token(),
        original_url=original_url,
    )


def rewrite_links(body_html: str, message) -> str:
    """
    Rewrite every http(s) href= in `body_html` to go through
    the click-tracking redirect endpoint.

    Skips:
      - mailto: links
      - The user's own unsubscribe URL (already handled by List-Unsubscribe)
      - localhost / 127.0.0.1 (dev environments)

    Each unique URL gets its own ClickToken row so we can track
    which links were clicked independently.
    """
    # Cache tokens per URL within one email to avoid duplicates
    url_token_cache: dict[str, str] = {}

    def _replace(match: re.Match) -> str:
        original_url = match.group(1)

        # Skip our own unsubscribe / tracking URLs
        if "/unsubscribe/" in original_url or "/t/" in original_url:
            return match.group(0)

        if original_url not in url_token_cache:
            token_obj = create_click_token(message, original_url)
            url_token_cache[original_url] = token_obj.token

        redirect_url = f"{_BASE_URL}/t/c/{url_token_cache[original_url]}/"
        return f'href="{redirect_url}"'

    return _HREF_RE.sub(_replace, body_html)


# ── Token resolution (used by tracking views) ─────────────────────────────────

def resolve_open_token(token: str):
    """
    Look up an OpenToken by its raw string.
    Returns (OpenToken, message) or (None, None).
    """
    from apps.events.models import OpenToken
    try:
        obj = OpenToken.objects.select_related("message__user").get(token=token)
        return obj, obj.message
    except OpenToken.DoesNotExist:
        logger.debug("resolve_open_token: unknown token %s", token[:16])
        return None, None


def resolve_click_token(token: str):
    """
    Look up a ClickToken by its raw string.
    Returns (ClickToken, message) or (None, None).
    """
    from apps.events.models import ClickToken
    try:
        obj = ClickToken.objects.select_related("message__user").get(token=token)
        return obj, obj.message
    except ClickToken.DoesNotExist:
        logger.debug("resolve_click_token: unknown token %s", token[:16])
        return None, None


# ── Request metadata helpers ──────────────────────────────────────────────────

def _get_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _get_ua(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")


# ── Record helpers (called from tracking views) ───────────────────────────────

def record_open_event(token: str, request) -> bool:
    """
    Resolve token, record the open event, fire webhook.
    Returns True if the token was found and processed.
    """
    token_obj, message = resolve_open_token(token)
    if not token_obj:
        return False

    ip = _get_ip(request)
    ua = _get_ua(request)

    # Records event + updates message status
    token_obj.record_open(ip=ip, ua=ua)

    # Fire webhook event (Phase 3.4)
    _fire_webhook(message, event_type="opened", metadata={"ip": ip, "ua": ua})

    logger.info("Open recorded for message %s", message.pk)
    return True


def record_click_event(token: str, request) -> str | None:
    """
    Resolve token, record the click event, fire webhook.
    Returns the original URL to redirect to, or None if token not found.
    """
    token_obj, message = resolve_click_token(token)
    if not token_obj:
        return None

    ip = _get_ip(request)
    ua = _get_ua(request)

    # Records event + updates message status
    token_obj.record_click(ip=ip, ua=ua)

    # Fire webhook event (Phase 3.4)
    _fire_webhook(
        message,
        event_type="clicked",
        metadata={"url": token_obj.original_url, "ip": ip, "ua": ua},
    )

    logger.info(
        "Click recorded for message %s → %s",
        message.pk, token_obj.original_url[:80],
    )
    return token_obj.original_url


# ── Webhook trigger (thin bridge to webhook_service) ─────────────────────────

def _fire_webhook(message, event_type: str, metadata: dict) -> None:
    """
    Enqueue a webhook delivery for the event.
    Imported lazily to avoid circular imports.
    """
    try:
        from services.webhook_service import dispatch_event
        dispatch_event(
            user=message.user,
            event_type=event_type,
            message=message,
            metadata=metadata,
        )
    except Exception as exc:
        # Never let a webhook failure break the tracking response
        logger.warning("_fire_webhook failed silently: %s", exc)