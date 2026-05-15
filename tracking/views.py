"""
Lightweight tracking views — no DRF, minimal overhead.

Endpoints:
  GET /t/o/<token>/   – 1×1 transparent GIF open-tracking pixel
  GET /t/c/<token>/   – click-tracking redirect (302 → original URL)

Both endpoints must respond as fast as possible:
  - No authentication required
  - Events are recorded synchronously (fast DB write)
  - Webhook dispatch is offloaded to Celery

Place: tracking/views.py
"""

import base64
import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from services.tracking_service import record_open_event, record_click_event

logger = logging.getLogger(__name__)

# ── 1×1 transparent GIF (standard tracking pixel) ────────────────────────────
# RFC 2397 data URI decoded to raw bytes — 43 bytes total
_TRANSPARENT_GIF = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

_GIF_HEADERS = {
    "Content-Type":  "image/gif",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma":        "no-cache",
    "Expires":       "0",
}


# ── Open pixel ────────────────────────────────────────────────────────────────

@never_cache
@require_GET
def open_pixel(request, token: str) -> HttpResponse:
    """
    Return a 1×1 transparent GIF and record an 'opened' event.

    Always returns the pixel even if the token is invalid,
    so email clients don't show a broken-image icon.
    """
    try:
        record_open_event(token, request)
    except Exception as exc:
        # Log but never crash — the pixel must always be served
        logger.warning("open_pixel error for token %s: %s", token[:16], exc)

    response = HttpResponse(_TRANSPARENT_GIF, content_type="image/gif")
    for key, val in _GIF_HEADERS.items():
        response[key] = val
    return response


# ── Click redirect ────────────────────────────────────────────────────────────

@never_cache
@require_GET
def click_redirect(request, token: str) -> HttpResponse:
    """
    Record a 'clicked' event and 302-redirect to the original URL.

    Falls back to the homepage if the token is unknown.
    """
    fallback_url = "/"

    try:
        original_url = record_click_event(token, request)
    except Exception as exc:
        logger.warning("click_redirect error for token %s: %s", token[:16], exc)
        original_url = None

    destination = original_url or fallback_url

    response = HttpResponseRedirect(destination)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response