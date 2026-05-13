"""
Top-level dashboard views: overview, message list/detail,
suppressions, unsubscribe landing, status page, and public landing page.

Place: web/views/dashboard.py
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpRequest, HttpResponse


# ── Public ────────────────────────────────────────────────────────────────────

def landing(request: HttpRequest) -> HttpResponse:
    """Public marketing / landing page."""
    return render(request, "public/landing.html")


def status_page(request: HttpRequest) -> HttpResponse:
    """System status page (public)."""
    return render(request, "public/status.html")


def unsubscribe(request: HttpRequest, token: str) -> HttpResponse:
    """
    Unsubscribe landing page.
    Phase 2 will wire this to the suppression service via the token.
    """
    # TODO (Phase 2): validate token, add to suppression list
    return render(request, "public/unsubscribe.html", {"token": token})


# ── Dashboard ─────────────────────────────────────────────────────────────────

def overview(request: HttpRequest) -> HttpResponse:
    """
    Dashboard home – shows stats summary charts.
    Stats are fetched via the analytics service (Phase 3).
    """
    context = {
        "page_title": "Overview",
        # Placeholder stats – replaced in Phase 3
        "stats": {
            "sent": 0, "delivered": 0, "opened": 0,
            "clicked": 0, "bounced": 0, "complained": 0,
        },
    }
    return render(request, "dashboard/index.html", context)


def messages(request: HttpRequest) -> HttpResponse:
    """Message history list with filters."""
    context = {
        "page_title": "Messages",
        "messages": [],   # Phase 3: queryset from email_messages app
    }
    return render(request, "dashboard/messages.html", context)


def message_detail(request: HttpRequest, pk) -> HttpResponse:
    """Single message detail: headers, status timeline, events."""
    # Phase 3: get_object_or_404(Message, pk=pk, user=request.user)
    context = {
        "page_title": "Message Detail",
        "message": None,
    }
    return render(request, "dashboard/message_detail.html", context)


def suppressions(request: HttpRequest) -> HttpResponse:
    """Suppression list viewer."""
    context = {
        "page_title": "Suppressions",
        "suppressions": [],   # Phase 2 wires this
    }
    return render(request, "dashboard/suppressions.html", context)