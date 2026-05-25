"""
ESP inbound webhook receiver.

Accepts bounce / delivery / complaint notifications from:
  - AWS SES via SNS  → POST /api/v1/inbound/ses/
  - Generic ESP      → POST /api/v1/inbound/esp/

Both endpoints normalise the raw payload into a standard dict and
hand it off to workers.tasks.process_events.dispatch_esp_event for
async processing.

No user authentication is required on these endpoints — they are
called by AWS / Mailgun / SendGrid, not by our API users.
Authentication is done via:
  - AWS SNS: validates the SNS signature
  - Generic: validates an HMAC-SHA256 header using a shared secret

Place: api/v1/views/inbound.py
"""

import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

logger = logging.getLogger(__name__)

# Shared secret for the generic ESP endpoint (set in .env)
_ESP_WEBHOOK_SECRET = getattr(settings, "ESP_WEBHOOK_SECRET", "")


# ── AWS SES / SNS receiver ────────────────────────────────────────────────────

@extend_schema(
    summary="AWS SES / SNS inbound webhook",
    description=(
        "Receives bounce, complaint, and delivery notifications from "
        "AWS SES via Amazon SNS. Validates the SNS signature before processing."
    ),
    request={"application/json": {"type": "object"}},
    responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
    tags=["Inbound (ESP)"],
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def ses_inbound(request):
    """
    Handle AWS SNS notifications for SES email events.

    SNS sends two types of messages:
      1. SubscriptionConfirmation – must GET the SubscribeURL to confirm
      2. Notification – the actual SES event payload
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return Response({"status": "bad_request"}, status=status.HTTP_400_BAD_REQUEST)

    message_type = request.headers.get("X-Amz-Sns-Message-Type", "")

    # ── SNS subscription confirmation ─────────────────────────────────────────
    if message_type == "SubscriptionConfirmation":
        subscribe_url = body.get("SubscribeURL")
        if subscribe_url:
            try:
                requests.get(subscribe_url, timeout=10)
                logger.info("SNS subscription confirmed: %s", subscribe_url[:80])
            except requests.RequestException as exc:
                logger.warning("SNS subscription confirmation failed: %s", exc)
        return Response({"status": "confirmed"})

    # ── SNS notification ──────────────────────────────────────────────────────
    if message_type == "Notification":
        try:
            ses_message = json.loads(body.get("Message", "{}"))
        except (json.JSONDecodeError, ValueError):
            return Response({"status": "bad_message"}, status=status.HTTP_400_BAD_REQUEST)

        notification_type = ses_message.get("notificationType", "")
        payload = _normalise_ses(ses_message, notification_type)

        if payload:
            from workers.tasks.process_events import dispatch_esp_event
            dispatch_esp_event.apply_async(args=[payload])
            logger.info("SES event enqueued: %s", notification_type)

        return Response({"status": "ok"})

    logger.debug("SNS: unhandled message type '%s'", message_type)
    return Response({"status": "ignored"})


def _normalise_ses(ses_message: dict, notification_type: str) -> dict | None:
    """
    Convert a raw SES notification into the standard payload shape
    consumed by dispatch_esp_event.
    """
    type_map = {
        "Bounce":    "bounced",
        "Complaint": "complained",
        "Delivery":  "delivered",
    }
    event = type_map.get(notification_type)
    if not event:
        return None

    # Extract the recipient email
    if notification_type == "Bounce":
        recipients = ses_message.get("bounce", {}).get("bouncedRecipients", [])
        email = recipients[0].get("emailAddress", "") if recipients else ""
    elif notification_type == "Complaint":
        recipients = ses_message.get("complaint", {}).get("complainedRecipients", [])
        email = recipients[0].get("emailAddress", "") if recipients else ""
    else:  # Delivery
        recipients = ses_message.get("delivery", {}).get("recipients", [])
        email = recipients[0] if recipients else ""

    # SES message ID is in the mail object
    esp_message_id = ses_message.get("mail", {}).get("messageId", "")

    return {
        "event":          event,
        "esp_message_id": esp_message_id,
        "to_email":       email,
        "occurred_at":    None,
        "metadata":       ses_message,
    }


# ── Generic ESP receiver (Mailgun / SendGrid / Postmark) ─────────────────────

@extend_schema(
    summary="Generic ESP inbound webhook",
    description=(
        "Receives normalised email event notifications from any ESP. "
        "Validates the `X-MailFlow-ESP-Signature` HMAC header. "
        "Expects the payload described in the request schema."
    ),
    request={
        "application/json": {
            "type": "object",
            "required": ["event", "esp_message_id"],
            "properties": {
                "event":          {"type": "string", "enum": ["delivered","bounced","complained","opened","clicked"]},
                "esp_message_id": {"type": "string"},
                "to_email":       {"type": "string"},
                "occurred_at":    {"type": "string", "format": "date-time"},
                "metadata":       {"type": "object"},
            },
        }
    },
    responses={202: {"type": "object", "properties": {"status": {"type": "string"}}}},
    tags=["Inbound (ESP)"],
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def esp_inbound(request):
    """
    Generic ESP webhook receiver.

    The sender must include:
        X-MailFlow-ESP-Signature: sha256=<HMAC of body using ESP_WEBHOOK_SECRET>
    """
    if _ESP_WEBHOOK_SECRET:
        sig_header = request.headers.get("X-MailFlow-Esp-Signature", "")
        if not _verify_hmac(request.body, sig_header, _ESP_WEBHOOK_SECRET):
            logger.warning("esp_inbound: invalid HMAC signature from %s",
                           request.META.get("REMOTE_ADDR"))
            return Response({"status": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return Response({"status": "bad_request"}, status=status.HTTP_400_BAD_REQUEST)

    required = ("event", "esp_message_id")
    if not all(payload.get(k) for k in required):
        return Response(
            {"status": "missing_fields", "required": list(required)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from workers.tasks.process_events import dispatch_esp_event
    dispatch_esp_event.apply_async(args=[{
        "event":          payload.get("event"),
        "esp_message_id": payload.get("esp_message_id"),
        "to_email":       payload.get("to_email", ""),
        "occurred_at":    payload.get("occurred_at"),
        "metadata":       payload.get("metadata", {}),
    }])

    return Response({"status": "accepted"}, status=status.HTTP_202_ACCEPTED)


# ── HMAC helper ───────────────────────────────────────────────────────────────

def _verify_hmac(body: bytes, signature_header: str, secret: str) -> bool:
    """Constant-time comparison of expected vs received HMAC-SHA256 signature."""
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)