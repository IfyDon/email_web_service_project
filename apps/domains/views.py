"""
DRF API views for domain management.

Endpoints mounted at /api/v1/domains/ via api/v1/urls.py:
  GET    /api/v1/domains/
  POST   /api/v1/domains/
  GET    /api/v1/domains/<id>/
  DELETE /api/v1/domains/<id>/
  POST   /api/v1/domains/<id>/verify/

Place: apps/domains/views.py
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsOwnerOrAdmin, IsVerifiedUser
from services.domain_service import add_domain, verify_domain, delete_domain
from .models import Domain
from .serializers import (
    DomainListSerializer,
    DomainDetailSerializer,
    DomainCreateSerializer,
    DomainVerifyResponseSerializer,
)


class DomainListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedUser]

    @extend_schema(responses={200: DomainListSerializer(many=True)})
    def get(self, request):
        """List all domains belonging to the current user."""
        domains = Domain.objects.filter(user=request.user)
        return Response(DomainListSerializer(domains, many=True).data)

    @extend_schema(
        request=DomainCreateSerializer,
        responses={201: DomainDetailSerializer},
    )
    def post(self, request):
        """Register a new sending domain and generate DKIM keys."""
        ser = DomainCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            domain = add_domain(user=request.user, name=ser.validated_data["name"])
        except ValueError as exc:
            return Response(
                {"error": {"code": "domain_exists", "message": str(exc)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            DomainDetailSerializer(domain).data,
            status=status.HTTP_201_CREATED,
        )


class DomainDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def _get_domain(self, request, pk):
        domain = get_object_or_404(Domain, pk=pk)
        self.check_object_permissions(request, domain)
        return domain

    @extend_schema(responses={200: DomainDetailSerializer})
    def get(self, request, pk):
        """Retrieve domain details including DNS records to publish."""
        return Response(DomainDetailSerializer(self._get_domain(request, pk)).data)

    def delete(self, request, pk):
        """Delete a domain (removes DKIM keys)."""
        domain = self._get_domain(request, pk)
        delete_domain(domain)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DomainVerifyView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(responses={200: DomainVerifyResponseSerializer})
    def post(self, request, pk):
        """
        Trigger a live DNS verification check for SPF, DKIM, and DMARC.
        Updates the domain's verification flags immediately (synchronous).

        For large-scale use this can be offloaded to a Celery task (Phase 3).
        """
        domain = get_object_or_404(Domain, pk=pk)
        self.check_object_permissions(request, domain)

        result = verify_domain(domain)

        response_status = (
            status.HTTP_200_OK if result["all_verified"]
            else status.HTTP_200_OK  # always 200 – caller checks all_verified
        )

        return Response(result, status=response_status)