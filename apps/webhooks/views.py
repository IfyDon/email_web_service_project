"""
DRF API views for webhook management.

Endpoints (mounted at /api/v1/webhooks/ via api/v1/urls.py):
  GET    /api/v1/webhooks/
  POST   /api/v1/webhooks/
  GET    /api/v1/webhooks/<id>/
  PATCH  /api/v1/webhooks/<id>/
  DELETE /api/v1/webhooks/<id>/
  POST   /api/v1/webhooks/<id>/test/
  GET    /api/v1/webhooks/<id>/deliveries/

Place: apps/webhooks/views.py
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

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


class WebhookListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: WebhookSerializer(many=True)})
    def get(self, request):
        """List all webhooks for the current user."""
        webhooks = Webhook.objects.filter(user=request.user)
        return Response(WebhookSerializer(webhooks, many=True).data)

    @extend_schema(
        request=WebhookCreateSerializer,
        responses={201: WebhookCreatedSerializer},
    )
    def post(self, request):
        """
        Register a new webhook endpoint.
        The signing secret is returned ONCE in this response.
        """
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


class WebhookDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def _get(self, request, pk) -> Webhook:
        wh = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, wh)
        return wh

    @extend_schema(responses={200: WebhookSerializer})
    def get(self, request, pk):
        return Response(WebhookSerializer(self._get(request, pk)).data)

    @extend_schema(
        request=WebhookUpdateSerializer,
        responses={200: WebhookSerializer},
    )
    def patch(self, request, pk):
        """Partial update — label, url, event_types, is_active."""
        webhook = self._get(request, pk)
        ser     = WebhookUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        webhook = update_webhook(webhook, **ser.validated_data)
        return Response(WebhookSerializer(webhook).data)

    def delete(self, request, pk):
        """Permanently delete a webhook and all its delivery logs."""
        webhook = self._get(request, pk)
        delete_webhook(webhook)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookTestView(APIView):
    """POST /api/v1/webhooks/<id>/test/ — send a live test ping."""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(responses={200: WebhookTestResponseSerializer})
    def post(self, request, pk):
        webhook = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, webhook)

        result = test_webhook(webhook)
        return Response(
            WebhookTestResponseSerializer(result).data,
            status=status.HTTP_200_OK,
        )


class WebhookDeliveryListView(APIView):
    """GET /api/v1/webhooks/<id>/deliveries/ — paginated delivery log."""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(responses={200: WebhookDeliverySerializer(many=True)})
    def get(self, request, pk):
        webhook = get_object_or_404(Webhook, pk=pk)
        self.check_object_permissions(request, webhook)

        qs = WebhookDelivery.objects.filter(webhook=webhook).order_by("-attempted_at")

        # Optional filter: ?status=success|failed|pending
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = StandardResultsPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            WebhookDeliverySerializer(page, many=True).data
        )