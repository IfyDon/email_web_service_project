"""
DRF API views for the email templates engine.

Endpoints (mounted at /api/v1/templates/ via api/v1/urls.py):
  GET    /api/v1/templates/
  POST   /api/v1/templates/
  GET    /api/v1/templates/<id>/
  PUT    /api/v1/templates/<id>/
  DELETE /api/v1/templates/<id>/
  POST   /api/v1/templates/<id>/preview/
  POST   /api/v1/templates/<id>/restore/
  GET    /api/v1/templates/<id>/versions/

Place: apps/templates_app/views.py
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsOwnerOrAdmin, IsVerifiedUser
from core.exceptions import TemplateRenderError
from services.template_service import (
    create_template,
    update_template,
    delete_template,
    preview_template,
)
from .models import EmailTemplate, TemplateVersion
from .serializers import (
    EmailTemplateListSerializer,
    EmailTemplateDetailSerializer,
    EmailTemplateCreateSerializer,
    EmailTemplateUpdateSerializer,
    TemplatePreviewSerializer,
    TemplatePreviewResponseSerializer,
    TemplateVersionSerializer,
    TemplateRestoreSerializer,
)


class TemplateListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedUser]

    @extend_schema(responses={200: EmailTemplateListSerializer(many=True)})
    def get(self, request):
        """List all active templates for the current user."""
        templates = EmailTemplate.objects.filter(
            user=request.user, is_active=True
        ).order_by("-created_at")
        return Response(EmailTemplateListSerializer(templates, many=True).data)

    @extend_schema(
        request=EmailTemplateCreateSerializer,
        responses={201: EmailTemplateDetailSerializer},
    )
    def post(self, request):
        """Create a new email template."""
        ser = EmailTemplateCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cd = ser.validated_data

        try:
            template = create_template(
                user=request.user,
                name=cd["name"],
                subject=cd["subject"],
                body_html=cd.get("body_html", ""),
                body_mjml=cd.get("body_mjml", ""),
                body_text=cd.get("body_text", ""),
                description=cd.get("description", ""),
                variable_schema=cd.get("variable_schema", {}),
            )
        except TemplateRenderError as exc:
            return Response(
                {"error": {"code": "template_render_error", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            EmailTemplateDetailSerializer(template).data,
            status=status.HTTP_201_CREATED,
        )


class TemplateDetailView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def _get(self, request, pk) -> EmailTemplate:
        t = get_object_or_404(EmailTemplate, pk=pk, is_active=True)
        self.check_object_permissions(request, t)
        return t

    @extend_schema(responses={200: EmailTemplateDetailSerializer})
    def get(self, request, pk):
        return Response(EmailTemplateDetailSerializer(self._get(request, pk)).data)

    @extend_schema(
        request=EmailTemplateUpdateSerializer,
        responses={200: EmailTemplateDetailSerializer},
    )
    def put(self, request, pk):
        """Full update — snapshots the current version first."""
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        """Partial update — same snapshot behaviour as PUT."""
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial: bool):
        template = self._get(request, pk)
        ser = EmailTemplateUpdateSerializer(data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        cd = ser.validated_data

        try:
            template = update_template(template, **cd)
        except TemplateRenderError as exc:
            return Response(
                {"error": {"code": "template_render_error", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(EmailTemplateDetailSerializer(template).data)

    def delete(self, request, pk):
        """Soft-delete (deactivate) a template."""
        template = self._get(request, pk)
        delete_template(template)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemplatePreviewView(APIView):
    """POST /api/v1/templates/<id>/preview/"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(
        request=TemplatePreviewSerializer,
        responses={200: TemplatePreviewResponseSerializer},
    )
    def post(self, request, pk):
        template = get_object_or_404(EmailTemplate, pk=pk, is_active=True)
        self.check_object_permissions(request, template)

        ser = TemplatePreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            result = preview_template(template, ser.validated_data.get("context", {}))
        except TemplateRenderError as exc:
            return Response(
                {"error": {"code": "template_render_error", "message": str(exc)}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(TemplatePreviewResponseSerializer(result).data)


class TemplateVersionListView(APIView):
    """GET /api/v1/templates/<id>/versions/"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    @extend_schema(responses={200: TemplateVersionSerializer(many=True)})
    def get(self, request, pk):
        template = get_object_or_404(EmailTemplate, pk=pk)
        self.check_object_permissions(request, template)
        versions = template.versions.all()
        return Response(TemplateVersionSerializer(versions, many=True).data)


class TemplateRestoreView(APIView):
    """POST /api/v1/templates/<id>/restore/"""
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def post(self, request, pk):
        template = get_object_or_404(EmailTemplate, pk=pk)
        self.check_object_permissions(request, template)

        ser = TemplateRestoreSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            template.restore_version(ser.validated_data["version_number"])
        except TemplateVersion.DoesNotExist:
            return Response(
                {"error": {"code": "version_not_found",
                           "message": "Version not found for this template."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(EmailTemplateDetailSerializer(template).data)