"""
DRF API views for webhook management.

Endpoints:
  GET    /api/v1/webhooks/
  POST   /api/v1/webhooks/
  GET    /api/v1/webhooks/<id>/
  PATCH  /api/v1/webhooks/<id>/
  DELETE /api/v1/webhooks/<id>/
  POST   /api/v1/webhooks/<id>/test/
  GET    /api/v1/webhooks/<id>/deliveries/
  POST   /api/v1/webhooks/<id>/deliveries/<delivery_id>/retry/

Place: apps/webhooks/views.py
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from core.permissions import IsOwnerOrAdmin
from core.pagination import StandardResultsPagination
from services.webhook_service import (
    create_webhook,
    update_webhook,
    delete_webhook,
    test_webhook,
)
from .models import Webhook, WebhookDelivery
from .serializers import (
    WebhookSerializer,
    WebhookCreatedSerializer,
    WebhookCreateSerializer,
    WebhookUpdateSerializer,
    WebhookDeliverySerializer,
    WebhookTestResponseSerializer,
)

logger = logging.getLogger(__name__)


# ── List + Create ─────────────────────────────────────────────────────────────

class WebhookListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List webhooks",
        responses={200: WebhookSerializer(many=True)},
        tags=["Webhooks"],
    )
    def get(self, request):
        webhooks = Webhook.objects.filter(user=request.user)
        return Response(WebhookSerializer(webhooks, many=True).data)

    @extend_schema(
        summary="Register webhook",
        description="The signing secret is returned **once** in this response.",
        request=WebhookCreateSerializer,
        responses={201: WebhookCreatedSerializer},
        tags=["Webhooks"],
    )
    def post(self, request):
        ser = WebhookCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cd  = ser.validated_data
        webhook = create_webhook(
            request.user,
            label=cd["label"],
            url=cd["url"],
            event_types=cd.get("event_types", []),
        )
        return Response(
            WebhookCreatedSerializer(webhook).data,
            status=status.HTTP_201_CREATED,
        )


# ── Detail + Update + Delete ──────────────────────────────────────────────────

class WebhookDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def _get(self, request, pk) -> Webhook:
        wh = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, wh)
        return wh

    @extend_schema(
        summary="Get webhook",
        responses={200: WebhookSerializer},
        tags=["Webhooks"],
    )
    def get(self, request, pk):
        return Response(WebhookSerializer(self._get(request, pk)).data)

    @extend_schema(
        summary="Update webhook",
        request=WebhookUpdateSerializer,
        responses={200: WebhookSerializer},
        tags=["Webhooks"],
    )
    def patch(self, request, pk):
        webhook = self._get(request, pk)
        ser     = WebhookUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        webhook = update_webhook(webhook, **ser.validated_data)
        return Response(WebhookSerializer(webhook).data)

    @extend_schema(
        summary="Delete webhook",
        responses={204: None},
        tags=["Webhooks"],
    )
    def delete(self, request, pk):
        delete_webhook(self._get(request, pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Test ping ─────────────────────────────────────────────────────────────────

class WebhookTestView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(
        summary="Send test ping",
        description="Send a synchronous test payload to the endpoint and return the HTTP result.",
        responses={200: WebhookTestResponseSerializer},
        tags=["Webhooks"],
    )
    def post(self, request, pk):
        webhook = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, webhook)
        result = test_webhook(webhook)
        return Response(WebhookTestResponseSerializer(result).data)


# ── Delivery log ──────────────────────────────────────────────────────────────

class WebhookDeliveryListView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(
        summary="List deliveries",
        description="Paginated delivery log. Filter by status or event_type.",
        parameters=[
            OpenApiParameter("status",     OpenApiTypes.STR,
                             description="pending | success | failed"),
            OpenApiParameter("event_type", OpenApiTypes.STR,
                             description="delivered | bounced | clicked | …"),
            OpenApiParameter("page",      OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT),
        ],
        responses={200: WebhookDeliverySerializer(many=True)},
        tags=["Webhooks"],
    )
    def get(self, request, pk):
        webhook = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, webhook)

        qs = WebhookDelivery.objects.filter(webhook=webhook).order_by("-attempted_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        event_filter = request.query_params.get("event_type")
        if event_filter:
            qs = qs.filter(event_type=event_filter)

        paginator = StandardResultsPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            WebhookDeliverySerializer(page, many=True).data
        )


# ── Delivery retry  ← THIS WAS THE MISSING CLASS ────────────────────────────

class WebhookDeliveryRetryView(APIView):
    """
    POST /api/v1/webhooks/<pk>/deliveries/<delivery_id>/retry/

    Re-enqueue a specific FAILED delivery for immediate retry.
    Only deliveries with status=failed can be retried.
    """
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(
        summary="Retry failed delivery",
        description="Re-enqueue a failed delivery for immediate retry.",
        responses={
            202: {
                "type": "object",
                "properties": {
                    "status":      {"type": "string", "example": "re_queued"},
                    "delivery_id": {"type": "string", "format": "uuid"},
                },
            },
            404: {"description": "Delivery not found or not in failed state."},
        },
        tags=["Webhooks"],
    )
    def post(self, request, pk, delivery_id):
        webhook = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, webhook)

        # Only allow retrying deliveries that are in FAILED state
        delivery = get_object_or_404(
            WebhookDelivery,
            pk=delivery_id,
            webhook=webhook,
            status=WebhookDelivery.Status.FAILED,
        )

        from workers.tasks.webhook_dispatch import deliver_webhook

        deliver_webhook.apply_async(
            kwargs={
                "webhook_id":  str(webhook.pk),
                "payload":     delivery.payload,
                "event_type":  delivery.event_type,
                "message_id":  str(delivery.message_id) if delivery.message_id else None,
                "attempt_no":  delivery.attempt_no + 1,
            },
            queue="webhooks",
        )

        logger.info(
            "Delivery %s manually re-queued by user %s",
            delivery.pk,
            request.user.email,
        )

        return Response(
            {"status": "re_queued", "delivery_id": str(delivery.pk)},
            status=status.HTTP_202_ACCEPTED,
        )