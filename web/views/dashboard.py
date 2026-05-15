"""
Top-level dashboard views.
Updated: messages(), message_detail() wired to real querysets.

Place: web/views/dashboard.py
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib import messages as flash_messages

from apps.email_messages.models import Message
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
    if request.method == "POST":
        success, email = consume_unsubscribe_token(token)
        return render(request, "public/unsubscribe.html", {
            "success": success,
            "email":   email,
            "error":   None if success else "This link is invalid or has already been used.",
        })
    return render(request, "public/unsubscribe.html", {
        "token": token, "confirm": True,
    })


# ── Dashboard overview ────────────────────────────────────────────────────────

def overview(request: HttpRequest) -> HttpResponse:
    from apps.email_messages.models import Message

    user = request.user
    base = Message.objects.filter(user=user)

    stats = {
        "sent":      base.filter(status__in=["delivered","opened","clicked"]).count(),
        "delivered": base.filter(status="delivered").count(),
        "opened":    base.filter(status="opened").count(),
        "clicked":   base.filter(status="clicked").count(),
        "bounced":   base.filter(status="bounced").count(),
        "complained":base.filter(status="complained").count(),
    }
    recent = base.order_by("-created_at")[:10]

    return render(request, "dashboard/index.html", {
        "page_title": "Overview",
        "stats":      stats,
        "recent_messages": recent,
    })


# ── Messages ──────────────────────────────────────────────────────────────────

def messages_view(request: HttpRequest) -> HttpResponse:
    """Paginated message history with filters."""
    qs      = Message.objects.filter(user=request.user)
    status  = request.GET.get("status", "")
    search  = request.GET.get("q", "")

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(to_email__icontains=search) | \
             qs.filter(subject__icontains=search)

    qs = qs.order_by("-created_at")

    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_obj  = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/messages.html", {
        "page_title":     "Messages",
        "messages_list":  page_obj,
        "status_filter":  status,
        "search_query":   search,
        "status_choices": Message.Status.choices,
    })


def message_detail(request: HttpRequest, pk) -> HttpResponse:
    message = get_object_or_404(
        Message.objects.prefetch_related("events", "attempts"),
        pk=pk, user=request.user,
    )
    return render(request, "dashboard/message_detail.html", {
        "page_title": f"Message — {message.subject[:50]}",
        "message":    message,
        "events":     message.events.order_by("occurred_at"),
        "attempts":   message.attempts.order_by("attempt_no"),
    })


# ── Suppressions ──────────────────────────────────────────────────────────────

"""
def suppressions(request: HttpRequest) -> HttpResponse:
    reason = request.GET.get("reason", "")
    sup_qs = get_suppressions(request.user, reason=reason or None)

    if request.method == "POST":
        action = request.POST.get("action")
        email  = request.POST.get("email", "").strip()

        if action == "add" and email:
            from services.suppression_service import add_manual
            add_manual(user=request.user, email=email,
                       description=request.POST.get("description", ""))
            flash_messages.success(request, f"'{email}' added to suppression list.")
            return redirect("web:suppressions")

        if action == "remove" and email:
            from services.suppression_service import remove_suppression
            removed = remove_suppression(user=request.user, email=email)
            if removed:
                flash_messages.success(request, f"'{email}' removed.")
            else:
                flash_messages.warning(request, f"'{email}' was not on the list.")
            return redirect("web:suppressions")

    return render(request, "dashboard/suppressions.html", {
        "page_title":     "Suppressions",
        "suppressions":   sup_qs,
        "reason_filter":  reason,
        "reason_choices": Suppression.Reason.choices,
    })
    """

def unsubscribe(request: HttpRequest, token: str) -> HttpResponse:
    # TODO Phase 2.4: wire to consume_unsubscribe_token service
    return render(request, "public/unsubscribe.html", {
        "token": token, "confirm": True,
    })


def overview(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/index.html", {
        "page_title": "Overview",
        "stats": {
            "sent": 0, "delivered": 0, "opened": 0,
            "clicked": 0, "bounced": 0, "complained": 0,
        },
        "recent_messages": [],
    })


def messages_view(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/messages.html", {
        "page_title":    "Messages",
        "messages_list": [],
    })


def message_detail(request: HttpRequest, pk) -> HttpResponse:
    return render(request, "dashboard/message_detail.html", {
        "page_title": "Message Detail",
        "message":    None,
    })


def suppressions(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/suppressions.html", {
        "page_title":   "Suppressions",
        "suppressions": [],
    })