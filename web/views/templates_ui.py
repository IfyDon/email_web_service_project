from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse

"""Email template management UI views.  Place: web/views/templates_ui.py"""


def template_list(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/templates.html", {
        "page_title": "Email Templates",
        "templates": [],   # Phase 2: EmailTemplate.objects.filter(user=request.user)
    })


def template_edit(request: HttpRequest, pk=None) -> HttpResponse:
    # pk=None → create new; pk set → edit existing
    # Phase 2: fetch or init EmailTemplate
    return render(request, "dashboard/template_edit.html", {
        "page_title": "Edit Template" if pk else "New Template",
        "template": None,
    })