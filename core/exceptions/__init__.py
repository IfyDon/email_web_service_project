"""
Shared DRF pagination classes.

Place: core/pagination/__init__.py
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Default pagination:
      GET /v1/messages?page=2&page_size=25
    Response envelope:
      { "count": 120, "next": "...", "previous": "...", "results": [...] }
    """

    page_size             = 50
    page_size_query_param = "page_size"
    max_page_size         = 200

    def get_paginated_response(self, data):
        return Response({
            "count":    self.page.paginator.count,
            "next":     self.get_next_link(),
            "previous": self.get_previous_link(),
            "results":  data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "results"],
            "properties": {
                "count":    {"type": "integer"},
                "next":     {"type": "string", "nullable": True},
                "previous": {"type": "string", "nullable": True},
                "results":  schema,
            },
        }


class CursorResultsPagination(PageNumberPagination):
    """
    Cursor-based pagination for high-volume message/event lists.
    Use on endpoints where offset pagination is too slow.
    """

    from rest_framework.pagination import CursorPagination

    page_size = 100
    ordering  = "-created_at"

class TemplateRenderError(Exception):
    """Raised when an email template fails to render."""

class QuotaExceededError(Exception):
    """Raised when a user exceeds their monthly sending quota."""


class SuppressionError(Exception):
    """Raised when a suppressed address is used."""

class RecipientSuppressed(Exception):
    """Raised when attempting to send to a suppressed address."""


class DomainVerificationError(Exception):
    """Raised when domain DNS verification fails."""


class QuotaExceededError(Exception):
    """Raised when a user exceeds their monthly sending quota."""


class APIKeyError(Exception):
    """Raised on invalid or revoked API key operations."""


class WebhookDeliveryError(Exception):
    """Raised when a webhook POST fails after all retries."""