"""
Tracking service — open pixel injection and link rewriting.

Phase 3.3 will implement full tracking token generation and event storage.
These stubs are wired into send_email.py now so the task doesn't fail to import.

Place: services/tracking_service.py
"""

import logging
import re
from urllib.parse import urlencode, quote

from django.conf import settings

logger = logging.getLogger(__name__)

_BASE_URL = getattr(settings, "APP_BASE_URL", "http://localhost:8000")


# ── Open tracking pixel ───────────────────────────────────────────────────────

def inject_tracking_pixel(body_html: str, message) -> str:
    """
    Inject a 1×1 transparent GIF tracking pixel just before </body>.
    Phase 3.3 will replace the stub token with a real signed token.
    """
    from apps.email_messages.models import Message
    token    = _make_open_token(message)
    pixel_url = f"{_BASE_URL}/t/o/{token}/"
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'alt="" style="display:none;border:none;" />'
    )

    if "</body>" in body_html:
        return body_html.replace("</body>", f"{pixel_tag}</body>", 1)
    return body_html + pixel_tag


# ── Link rewriting ────────────────────────────────────────────────────────────

_HREF_RE = re.compile(r'href="(https?://[^"]+)"', re.IGNORECASE)


def rewrite_links(body_html: str, message) -> str:
    """
    Rewrite all http(s) href= attributes to go through the click-tracking
    redirect endpoint.  Phase 3.3 will add signed token storage.
    """
    def _replace(match):
        original_url = match.group(1)
        token        = _make_click_token(message, original_url)
        redirect_url = f"{_BASE_URL}/t/c/{token}/"
        return f'href="{redirect_url}"'

    return _HREF_RE.sub(_replace, body_html)


# ── Token helpers (stub — replaced in Phase 3.3) ─────────────────────────────

def _make_open_token(message) -> str:
    """
    Return a URL-safe token that encodes the message id.
    Phase 3.3 replaces this with a signed, DB-backed token.
    """
    import base64
    raw = f"open:{message.pk}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _make_click_token(message, original_url: str) -> str:
    """
    Return a URL-safe token that encodes the message id + original URL.
    Phase 3.3 replaces this with a signed, DB-backed ClickToken row.
    """
    import base64, hashlib
    raw = f"click:{message.pk}:{original_url}"
    # Keep tokens short: hash the URL portion
    h   = hashlib.sha256(original_url.encode()).hexdigest()[:16]
    raw = f"click:{message.pk}:{h}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


# ── Decode (used by tracking views in Phase 3.3) ─────────────────────────────

def decode_open_token(token: str) -> str | None:
    """Decode an open token → message_id string. Returns None on error."""
    try:
        import base64
        # Re-add padding
        padded = token + "=" * (-len(token) % 4)
        raw    = base64.urlsafe_b64decode(padded).decode()
        _, message_id = raw.split(":", 1)
        return message_id
    except Exception:
        return None


def decode_click_token(token: str) -> tuple[str | None, str | None]:
    """Decode a click token → (message_id, url_hash). Returns (None, None) on error."""
    try:
        import base64
        padded = token + "=" * (-len(token) % 4)
        raw    = base64.urlsafe_b64decode(padded).decode()
        parts  = raw.split(":", 2)
        return parts[1], parts[2] if len(parts) > 2 else None
    except Exception:
        return None, None