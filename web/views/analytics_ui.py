"""Analytics UI view.  Place: web/views/analytics_ui.py"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse

def analytics(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/analytics.html", {
        "page_title": "Analytics",
        "chart_data": {},   # Phase 3: analytics_service.get_chart_data(request.user)
    })
