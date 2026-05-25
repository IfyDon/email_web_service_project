"""
Send API views — single and bulk email dispatch.

Updated for Phase 4.1: applies SendRateThrottle on top of global throttles.

Place: api/v1/views/send.py
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsVerifiedUser, HasAPIKey, QuotaNotExceeded
from core.throttling import SendRateThrottle
from core.exceptions import (
    QuotaExceeded,
    DomainNotVerified,
    RecipientSuppressed,
    TemplateRenderError,
)
from services.email_service import send_single, send_bulk
from api.v1.serializers.send import (
    SendSerializer,
    BulkSendSerializer,
    SendResponseSerializer,
    BulkSendResponseSerializer,
)

logger = logging.getLogger(__name__)


class SendView(APIView):
    """POST /api/v1/send — enqueue a single email (returns 202 immediately)."""

    permission_classes = [IsVerifiedUser, HasAPIKey, QuotaNotExceeded]
    throttle_classes   = [SendRateThrottle]      # 30 send-requests / min

    @extend_schema(
        summary="Send a single email",
        description=(
            "Enqueue one transactional email. Returns `202 Accepted` with "
            "a `message_id` immediately; delivery is asynchronous."
        ),
        request=SendSerializer,
        responses={202: SendResponseSerializer},
        tags=["Send"],
    )
    def post(self, request):
        ser = SendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cd  = ser.validated_data

        try:
            message = send_single(
                request.user,
                to_email          = cd["to_email"],
                to_name           = cd.get("to_name", ""),
                from_email        = cd.get("from_email") or None,
                from_name         = cd.get("from_name", ""),
                reply_to          = cd.get("reply_to", ""),
                subject           = cd.get("subject", ""),
                body_html         = cd.get("body_html", ""),
                body_text         = cd.get("body_text", ""),
                template_id       = str(cd["template_id"]) if cd.get("template_id") else None,
                template_context  = cd.get("template_context", {}),
                domain_id         = str(cd["domain_id"]) if cd.get("domain_id") else None,
                tags              = cd.get("tags", []),
                metadata          = cd.get("metadata", {}),
                track_opens       = cd.get("track_opens", True),
                track_clicks      = cd.get("track_clicks", True),
            )
        except QuotaExceeded as exc:
            return Response(
                {"error": {"code": "quota_exceeded",        "message": str(exc)}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except DomainNotVerified as exc:
            return Response(
                {"error": {"code": "domain_not_verified",   "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except RecipientSuppressed as exc:
            return Response(
                {"error": {"code": "recipient_suppressed",  "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except TemplateRenderError as exc:
            return Response(
                {"error": {"code": "template_render_error", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "invalid_request",       "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            SendResponseSerializer({
                "message_id": message.pk,
                "status":     message.status,
                "queued_at":  message.queued_at,
            }).data,
            status=status.HTTP_202_ACCEPTED,
        )


class BulkSendView(APIView):
    """POST /api/v1/send/bulk — fan-out to up to 1 000 recipients."""

    permission_classes = [IsVerifiedUser, HasAPIKey, QuotaNotExceeded]
    throttle_classes   = [SendRateThrottle]

    @extend_schema(
        summary="Bulk send",
        description=(
            "Fan-out up to 1 000 personalised emails in a single call. "
            "Each recipient may carry its own subject, body, and context variables."
        ),
        request=BulkSendSerializer,
        responses={202: BulkSendResponseSerializer},
        tags=["Send"],
    )
    def post(self, request):
        ser = BulkSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cd  = ser.validated_data

        try:
            queued_messages = send_bulk(
                request.user,
                recipients  = cd["recipients"],
                subject     = cd.get("subject", ""),
                from_email  = cd.get("from_email") or None,
                from_name   = cd.get("from_name", ""),
                body_html   = cd.get("body_html", ""),
                body_text   = cd.get("body_text", ""),
                template_id = str(cd["template_id"]) if cd.get("template_id") else None,
                domain_id   = str(cd["domain_id"])   if cd.get("domain_id")   else None,
                tags        = cd.get("tags", []),
                track_opens = cd.get("track_opens", True),
                track_clicks= cd.get("track_clicks", True),
            )
        except QuotaExceeded as exc:
            return Response(
                {"error": {"code": "quota_exceeded",      "message": str(exc)}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except DomainNotVerified as exc:
            return Response(
                {"error": {"code": "domain_not_verified", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "invalid_request",     "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total = len(cd["recipients"])
        return Response(
            BulkSendResponseSerializer({
                "queued":   len(queued_messages),
                "skipped":  total - len(queued_messages),
                "messages": [
                    {"message_id": m.pk, "status": m.status, "queued_at": m.queued_at}
                    for m in queued_messages
                ],
            }).data,
            status=status.HTTP_202_ACCEPTED,
        )