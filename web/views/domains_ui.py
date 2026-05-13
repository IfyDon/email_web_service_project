"""
Dashboard UI views for domain management.
Phase 1: stubs only - full implementation in Phase 2.

Place: web/views/domains_ui.py
"""

import re
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpRequest, HttpResponse

# Phase 2 imports - uncomment when models and services are built
# from apps.domains.models import Domain
# from services.domain_service import add_domain, verify_domain, delete_domain

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)


def _is_valid_domain(name: str) -> bool:
    return bool(_DOMAIN_RE.match(name.strip().lower().rstrip(".")))


def domain_list(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/domains.html", {
        "page_title": "Sending Domains",
        "domains":    [],   # Phase 2: Domain.objects.filter(user=request.user)
    })


def domain_add(request: HttpRequest) -> HttpResponse:
    error = None
    if request.method == "POST":
        name = request.POST.get("name", "").strip().lower().rstrip(".")
        if not name:
            error = "Please enter a domain name."
        elif not _is_valid_domain(name):
            error = f"'{name}' is not a valid domain name."
        else:
            # TODO Phase 2: domain = add_domain(user=request.user, name=name)
            messages.success(request, f"Domain '{name}' will be added in Phase 2.")
            return redirect("web:domains")

    return render(request, "dashboard/domain_add.html", {
        "page_title": "Add Domain",
        "error":      error,
    })


def domain_detail(request: HttpRequest, pk) -> HttpResponse:
    # TODO Phase 2: domain = get_object_or_404(Domain, pk=pk, user=request.user)
    return render(request, "dashboard/domain_detail.html", {
        "page_title":  "Domain Detail",
        "domain":      None,
        "dns_records": [],
    })


@require_POST
def domain_verify(request: HttpRequest, pk) -> HttpResponse:
    # TODO Phase 2: verify_domain(domain)
    messages.info(request, "Domain verification available in Phase 2.")
    return redirect("web:domains")


@require_POST
def domain_delete(request: HttpRequest, pk) -> HttpResponse:
    # TODO Phase 2: delete_domain(domain)
    messages.info(request, "Domain deletion available in Phase 2.")
    return redirect("web:domains")