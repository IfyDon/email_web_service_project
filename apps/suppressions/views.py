"""
DRF API views for suppression list management.

Endpoints (mounted at /api/v1/suppressions/):
  GET    /api/v1/suppressions/          list (filterable by reason)
  POST   /api/v1/suppressions/          add manual suppression
  DELETE /api/v1/suppressions/<id>/     remove by PK
  POST   /api/v1/suppressions/check/    check if an email is suppressed

Place: apps/suppressions/views.py
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsOwnerOrAdmin
from services.suppression_service import (
    add_manual,
    remove_suppression,
    get_suppressions,
)
from .models import Suppression
from .serializers import (
    SuppressionSerializer,
    SuppressionCreateSerializer,
)


class SuppressionListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SuppressionSerializer(many=True)})
    def get(self, request):
        """
        List suppressions.
        Optional query params: ?reason=bounce|complaint|unsubscribe|manual
        """
        reason = request.query_params.get("reason")
        qs     = get_suppressions(request.user, reason=reason)
        return Response(SuppressionSerializer(qs, many=True).data)

    @extend_schema(
        request=SuppressionCreateSerializer,
        responses={201: SuppressionSerializer},
    )
    def post(self, request):
        """Manually add an email address to the suppression list."""
        ser = SuppressionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        sup = add_manual(
            user=request.user,
            email=ser.validated_data["email"],
            description=ser.validated_data.get("description", ""),
        )
        return Response(SuppressionSerializer(sup).data, status=status.HTTP_201_CREATED)


class SuppressionDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def delete(self, request, pk):
        """Remove a suppression by PK (allow sending to the address again)."""
        sup = get_object_or_404(Suppression, pk=pk, user=request.user)
        sup.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuppressionCheckView(APIView):
    """POST /api/v1/suppressions/check/ — quick suppression lookup."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"error": {"code": "missing_email", "message": "email is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        suppressed = Suppression.is_suppressed(request.user, email)
        return Response({"email": email, "suppressed": suppressed})