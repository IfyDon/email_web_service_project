import base64
import logging
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

_PIXEL_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


@never_cache
@require_GET
def track_open(request, token):
    logger.debug("Open tracked: token=%s", token)
    return HttpResponse(_PIXEL_GIF, content_type="image/gif")


@never_cache
@require_GET
def track_click(request, token, encoded):
    try:
        padding = 4 - len(encoded) % 4
        original_url = base64.urlsafe_b64decode(encoded + "=" * padding).decode()
    except Exception:
        return HttpResponseBadRequest("Invalid tracking link.")
    logger.debug("Click tracked: token=%s", token)
    return HttpResponseRedirect(original_url)


@never_cache
@require_GET
def unsubscribe(request, token):
    logger.debug("Unsubscribe: token=%s", token)
    return HttpResponse(
        "<html><body><h2>You have been unsubscribed.</h2></body></html>",
        content_type="text/html",
    )
