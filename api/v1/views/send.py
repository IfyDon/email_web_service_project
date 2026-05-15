"""
Send API views.

POST /api/v1/send       – single email
POST /api/v1/send/bulk  – up to 1 000 recipients

Both return immediately with status=queued.
Actual delivery happens asynchronously via Celery.

Place: api/v1/views/send.py
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsVerifiedUser, HasAPIKey, QuotaNotExceeded
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
    """POST /api/v1/send — single email dispatch."""

    permission_classes = [IsVerifiedUser, HasAPIKey, QuotaNotExceeded]

    @extend_schema(
        request=SendSerializer,
        responses={202: SendResponseSerializer},
    )
    def post(self, request):
        ser = SendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cd  = ser.validated_data

        try:
            message = send_single(
                request.user,
                to_email=cd["to_email"],
                to_name=cd.get("to_name", ""),
                from_email=cd.get("from_email") or None,
                from_name=cd.get("from_name", ""),
                reply_to=cd.get("reply_to", ""),
                subject=cd.get("subject", ""),
                body_html=cd.get("body_html", ""),
                body_text=cd.get("body_text", ""),
                template_id=str(cd["template_id"]) if cd.get("template_id") else None,
                template_context=cd.get("template_context", {}),
                domain_id=str(cd["domain_id"]) if cd.get("domain_id") else None,
                tags=cd.get("tags", []),
                metadata=cd.get("metadata", {}),
                track_opens=cd.get("track_opens", True),
                track_clicks=cd.get("track_clicks", True),
            )
        except QuotaExceeded as exc:
            return Response(
                {"error": {"code": "quota_exceeded", "message": str(exc)}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except DomainNotVerified as exc:
            return Response(
                {"error": {"code": "domain_not_verified", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except RecipientSuppressed as exc:
            return Response(
                {"error": {"code": "recipient_suppressed", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except TemplateRenderError as exc:
            return Response(
                {"error": {"code": "template_render_error", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "invalid_request", "message": str(exc)}},
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

    @extend_schema(
        request=BulkSendSerializer,
        responses={202: BulkSendResponseSerializer},
    )
    def post(self, request):
        ser = BulkSendSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cd  = ser.validated_data

        try:
            messages = send_bulk(
                request.user,
                recipients=cd["recipients"],
                subject=cd.get("subject", ""),
                from_email=cd.get("from_email") or None,
                from_name=cd.get("from_name", ""),
                body_html=cd.get("body_html", ""),
                body_text=cd.get("body_text", ""),
                template_id=str(cd["template_id"]) if cd.get("template_id") else None,
                domain_id=str(cd["domain_id"]) if cd.get("domain_id") else None,
                tags=cd.get("tags", []),
                track_opens=cd.get("track_opens", True),
                track_clicks=cd.get("track_clicks", True),
            )
        except QuotaExceeded as exc:
            return Response(
                {"error": {"code": "quota_exceeded", "message": str(exc)}},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except DomainNotVerified as exc:
            return Response(
                {"error": {"code": "domain_not_verified", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "invalid_request", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_recipients = len(cd["recipients"])
        queued_messages  = [
            {"message_id": m.pk, "status": m.status, "queued_at": m.queued_at}
            for m in messages
        ]

        return Response(
            BulkSendResponseSerializer({
                "queued":   len(messages),
                "skipped":  total_recipients - len(messages),
                "messages": queued_messages,
            }).data,
            status=status.HTTP_202_ACCEPTED,
        )