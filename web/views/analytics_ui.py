"""
Dashboard analytics view — powers the analytics page chart and summary cards.

Place: web/views/analytics_ui.py
"""

import json
from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from services.analytics_service import get_summary, get_timeline, get_top_domains


def analytics(request: HttpRequest) -> HttpResponse:
    today     = timezone.now().date()
    date_from = today - timedelta(days=29)   # last 30 days

    summary    = get_summary(request.user, date_from=date_from, date_to=today)
    timeline   = get_timeline(request.user, date_from=date_from, date_to=today)
    top_domains = get_top_domains(request.user, date_from=date_from, date_to=today)

    # Prepare chart.js-friendly series arrays
    labels     = [row["date"] for row in timeline]
    sent_data  = [row["sent"]      for row in timeline]
    open_data  = [row["opened"]    for row in timeline]
    click_data = [row["clicked"]   for row in timeline]
    bounce_data= [row["bounced"]   for row in timeline]

    return render(request, "dashboard/analytics.html", {
        "page_title":   "Analytics",
        "summary":      summary,
        "top_domains":  top_domains,
        # Serialised for Chart.js
        "chart_labels":      json.dumps(labels),
        "chart_sent":        json.dumps(sent_data),
        "chart_opened":      json.dumps(open_data),
        "chart_clicked":     json.dumps(click_data),
        "chart_bounced":     json.dumps(bounce_data),
        "date_from":         date_from,
        "date_to":           today,
    })