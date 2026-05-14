"""
Top-level dashboard views.
Updated: unsubscribe() now calls suppression_service.

Place: web/views/dashboard.py
"""

from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.contrib import messages

from services.suppression_service import (
    consume_unsubscribe_token,
    get_suppressions,
)
from apps.suppressions.models import Suppression


# ── Public ────────────────────────────────────────────────────────────────────

def landing(request: HttpRequest) -> HttpResponse:
    return render(request, "public/landing.html")


def status_page(request: HttpRequest) -> HttpResponse:
    return render(request, "public/status.html")


def unsubscribe(request: HttpRequest, token: str) -> HttpResponse:
    """
    Public unsubscribe landing page.
    GET  — show a confirmation page.
    POST — consume the token, suppress the email, show success.
    """
    if request.method == "POST":
        success, email = consume_unsubscribe_token(token)
        if success:
            return render(request, "public/unsubscribe.html", {
                "success": True,
                "email":   email,
            })
        return render(request, "public/unsubscribe.html", {
            "success": False,
            "error":   "This unsubscribe link is invalid or has already been used.",
        })

    # GET — show confirm page
    return render(request, "public/unsubscribe.html", {
        "token":   token,
        "confirm": True,
    })


# ── Dashboard ─────────────────────────────────────────────────────────────────

def overview(request: HttpRequest) -> HttpResponse:
    context = {
        "page_title": "Overview",
        "stats": {
            "sent": 0, "delivered": 0, "opened": 0,
            "clicked": 0, "bounced": 0, "complained": 0,
        },
    }
    return render(request, "dashboard/index.html", context)


def messages_view(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/messages.html", {
        "page_title": "Messages",
        "messages_list": [],
    })


def message_detail(request: HttpRequest, pk) -> HttpResponse:
    return render(request, "dashboard/message_detail.html", {
        "page_title": "Message Detail",
        "message": None,
    })


def suppressions(request: HttpRequest) -> HttpResponse:
    """
    GET  — list all suppressions.
    POST — manual add or remove.
    """
    reason  = request.GET.get("reason", "")
    sup_qs  = get_suppressions(request.user, reason=reason or None)

    if request.method == "POST":
        action = request.POST.get("action")
        email  = request.POST.get("email", "").strip()

        if action == "add" and email:
            from services.suppression_service import add_manual
            add_manual(user=request.user, email=email,
                       description=request.POST.get("description", ""))
            messages.success(request, f"'{email}' added to suppression list.")
            return redirect("web:suppressions")

        if action == "remove" and email:
            from services.suppression_service import remove_suppression
            removed = remove_suppression(user=request.user, email=email)
            if removed:
                messages.success(request, f"'{email}' removed from suppression list.")
            else:
                messages.warning(request, f"'{email}' was not on the suppression list.")
            return redirect("web:suppressions")

    return render(request, "dashboard/suppressions.html", {
        "page_title":  "Suppressions",
        "suppressions": sup_qs,
        "reason_filter": reason,
        "reason_choices": Suppression.Reason.choices,
    })