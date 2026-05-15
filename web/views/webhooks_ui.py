"""
Dashboard UI views for webhook management.

Place: web/views/webhooks_ui.py
"""

import json
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpRequest, HttpResponse, JsonResponse

from apps.webhooks.models import Webhook, WebhookDelivery, ALL_EVENT_TYPES
from services.webhook_service import (
    create_webhook,
    update_webhook,
    delete_webhook,
    test_webhook,
)


def webhook_list(request: HttpRequest) -> HttpResponse:
    webhooks = Webhook.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/webhooks.html", {
        "page_title": "Webhooks",
        "webhooks":   webhooks,
    })


def webhook_add(request: HttpRequest) -> HttpResponse:
    error = None

    if request.method == "POST":
        label = request.POST.get("label", "").strip()
        url   = request.POST.get("url", "").strip()
        event_types = request.POST.getlist("event_types")  # multi-select

        if not label or not url:
            error = "Label and URL are required."
        else:
            webhook = create_webhook(
                request.user,
                label=label,
                url=url,
                event_types=event_types or [],
            )
            # Store secret in session — shown once on next page
            request.session["new_webhook_secret"] = webhook.secret
            request.session["new_webhook_id"]     = str(webhook.pk)
            messages.success(request, f"Webhook '{label}' created.")
            return redirect("web:webhook-reveal")

    return render(request, "dashboard/webhook_add.html", {
        "page_title":   "Add Webhook",
        "event_types":  ALL_EVENT_TYPES,
        "error":        error,
    })


def webhook_reveal(request: HttpRequest) -> HttpResponse:
    """Show the signing secret once, then clear it from session."""
    secret = request.session.pop("new_webhook_secret", None)
    wh_id  = request.session.pop("new_webhook_id",     None)

    if not secret:
        messages.warning(request, "No webhook secret to display.")
        return redirect("web:webhooks")

    webhook = get_object_or_404(Webhook, pk=wh_id, user=request.user)
    return render(request, "dashboard/webhook_reveal.html", {
        "page_title": "Save Your Webhook Secret",
        "webhook":    webhook,
        "secret":     secret,
    })


def webhook_detail(request: HttpRequest, pk) -> HttpResponse:
    webhook   = get_object_or_404(Webhook, pk=pk, user=request.user)
    deliveries = WebhookDelivery.objects.filter(webhook=webhook).order_by("-attempted_at")[:50]

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update":
            label       = request.POST.get("label", "").strip()
            url         = request.POST.get("url", "").strip()
            event_types = request.POST.getlist("event_types")
            is_active   = request.POST.get("is_active") == "on"
            update_webhook(
                webhook,
                label=label or None,
                url=url or None,
                event_types=event_types,
                is_active=is_active,
            )
            messages.success(request, "Webhook updated.")
            return redirect("web:webhook-detail", pk=webhook.pk)

    return render(request, "dashboard/webhook_detail.html", {
        "page_title":  f"Webhook — {webhook.label}",
        "webhook":     webhook,
        "deliveries":  deliveries,
        "event_types": ALL_EVENT_TYPES,
    })


def webhook_test_ajax(request: HttpRequest, pk) -> JsonResponse:
    """POST — AJAX live test ping from the dashboard."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    webhook = get_object_or_404(Webhook, pk=pk, user=request.user)
    result  = test_webhook(webhook)
    return JsonResponse(result)


@require_POST
def webhook_delete(request: HttpRequest, pk) -> HttpResponse:
    webhook = get_object_or_404(Webhook, pk=pk, user=request.user)
    label   = webhook.label
    delete_webhook(webhook)
    messages.success(request, f"Webhook '{label}' deleted.")
    return redirect("web:webhooks")