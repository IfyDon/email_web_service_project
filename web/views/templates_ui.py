"""
Dashboard UI views for email template management.

Place: web/views/templates_ui.py
"""

import json
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.templates_app.models import EmailTemplate
from services.template_service import (
    create_template,
    update_template,
    delete_template,
    preview_template,
)
from core.exceptions import TemplateRenderError


def template_list(request: HttpRequest) -> HttpResponse:
    tmpls = EmailTemplate.objects.filter(
        user=request.user, is_active=True
    ).order_by("-created_at")
    return render(request, "dashboard/templates.html", {
        "page_title": "Email Templates",
        "templates":  tmpls,
    })


def template_edit(request: HttpRequest, pk=None) -> HttpResponse:
    """
    GET  — render the editor (create or edit).
    POST — persist changes, redirect to list.
    """
    template = None
    if pk:
        template = get_object_or_404(EmailTemplate, pk=pk, user=request.user, is_active=True)

    if request.method == "POST":
        data = {
            "name":             request.POST.get("name", "").strip(),
            "subject":          request.POST.get("subject", "").strip(),
            "body_html":        request.POST.get("body_html", ""),
            "body_mjml":        request.POST.get("body_mjml", ""),
            "body_text":        request.POST.get("body_text", ""),
            "description":      request.POST.get("description", ""),
            "variable_schema":  _parse_variable_schema(request.POST.get("variable_schema", "{}")),
        }

        if not data["name"]:
            messages.error(request, "Template name is required.")
            return render(request, "dashboard/template_edit.html", {
                "page_title": "Edit Template" if template else "New Template",
                "template": template,
            })

        try:
            if template:
                update_template(template, **data)
                messages.success(request, f"Template '{template.name}' updated.")
            else:
                template = create_template(user=request.user, **data)
                messages.success(request, f"Template '{template.name}' created.")
            return redirect("web:templates")
        except TemplateRenderError as exc:
            messages.error(request, f"Template error: {exc}")

    return render(request, "dashboard/template_edit.html", {
        "page_title":   "Edit Template" if template else "New Template",
        "template":     template,
        "variable_schema_json": json.dumps(
            template.variable_schema if template else {}
        ),
    })


def template_preview_ajax(request: HttpRequest, pk) -> JsonResponse:
    """
    POST — AJAX endpoint used by the editor to preview rendered output.
    Returns JSON: { subject, body_html, body_text }.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    template = get_object_or_404(EmailTemplate, pk=pk, user=request.user)
    try:
        body = json.loads(request.body)
        context = body.get("context", {})
        result  = preview_template(template, context)
        return JsonResponse(result)
    except TemplateRenderError as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except Exception as exc:
        return JsonResponse({"error": "Preview failed."}, status=500)


@require_POST
def template_delete(request: HttpRequest, pk) -> HttpResponse:
    template = get_object_or_404(EmailTemplate, pk=pk, user=request.user)
    name = template.name
    delete_template(template)
    messages.success(request, f"Template '{name}' deleted.")
    return redirect("web:templates")


# ── Internal helper ───────────────────────────────────────────────────────────

def _parse_variable_schema(raw: str) -> dict:
    """Safely parse the variable_schema JSON from the form."""
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}