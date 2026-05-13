
"""Webhook management UI views.  Place: web/views/webhooks_ui.py"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST


def webhook_list(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/webhooks.html", {
        "page_title": "Webhooks",
        "webhooks": [],   # Phase 3: Webhook.objects.filter(user=request.user)
    })


def webhook_add(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        pass  # Phase 3
    return render(request, "dashboard/webhook_add.html", {"page_title": "Add Webhook"})


@require_POST
def webhook_delete(request: HttpRequest, pk) -> HttpResponse:
    # Phase 3: delete + redirect
    return redirect("web:webhooks")
