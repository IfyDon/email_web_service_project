"""
Custom DRF exception handler and project-wide exception classes.

Place: core/exceptions/__init__.py
"""

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import APIException, Throttled
from rest_framework import status
from rest_framework.response import Response


# ── Custom exception handler ──────────────────────────────────────────────────

def custom_exception_handler(exc, context):
    """
    Wraps DRF's default handler so every error response has the shape:

        {
            "error": {
                "code":    "throttled",
                "message": "Request was throttled. Retry after 42 seconds.",
                "retry_after": 42    # only on Throttled
            }
        }
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        error_payload: dict = {
            "code":    _get_code(exc),
            "message": _flatten(response.data),
        }

        # Add retry_after for throttle responses
        if isinstance(exc, Throttled) and exc.wait is not None:
            error_payload["retry_after"] = int(exc.wait)
            response["Retry-After"] = str(int(exc.wait))

        response.data = {"error": error_payload}

    return response


def _get_code(exc) -> str:
    if hasattr(exc, "default_code"):
        return exc.default_code
    return "error"


def _flatten(data) -> str:
    if isinstance(data, dict):
        for key in ("detail", "non_field_errors"):
            if key in data:
                return _flatten(data[key])
        return "; ".join(f"{k}: {_flatten(v)}" for k, v in data.items())
    if isinstance(data, list):
        return " ".join(_flatten(item) for item in data)
    return str(data)


# ── Project-specific exceptions ───────────────────────────────────────────────

class QuotaExceeded(APIException):
    status_code  = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Monthly sending quota exceeded. Upgrade your plan or wait for the monthly reset."
    default_code   = "quota_exceeded"


class DomainNotVerified(APIException):
    status_code  = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The sending domain has not been verified."
    default_code   = "domain_not_verified"


class RecipientSuppressed(APIException):
    status_code  = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "One or more recipients are on the suppression list."
    default_code   = "recipient_suppressed"


class TemplateRenderError(APIException):
    status_code  = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Failed to render the email template."
    default_code   = "template_render_error"


class WebhookDeliveryFailed(APIException):
    status_code  = status.HTTP_502_BAD_GATEWAY
    default_detail = "Webhook delivery failed after maximum retries."
    default_code   = "webhook_delivery_failed"


class DomainExists(APIException):
    status_code  = status.HTTP_409_CONFLICT
    default_detail = "This domain is already registered."
    default_code   = "domain_exists"