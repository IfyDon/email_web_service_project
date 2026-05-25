"""
Version-1 API URL registry — final.

Place: api/v1/urls.py
"""

from django.urls import path, include
from api.v1.views import send, messages, stats, inbound

app_name = "v1"

urlpatterns = [
    # ── Phase 2.1 – Auth & API key management ─────────────────────────────────
    path("auth/",         include("apps.authentication.urls", namespace="authentication")),

    # ── Phase 2.2 – Domain verification ──────────────────────────────────────
    path("domains/",      include("apps.domains.urls",        namespace="domains")),

    # ── Phase 2.3 – Email templates ───────────────────────────────────────────
    path("templates/",    include("apps.templates_app.urls",  namespace="templates_app")),

    # ── Phase 2.4 – Suppression list ─────────────────────────────────────────
    path("suppressions/", include("apps.suppressions.urls",   namespace="suppressions")),

    # ── Phase 3.1 – Email send ────────────────────────────────────────────────
    path("send",          send.SendView.as_view(),            name="send"),
    path("send/bulk",     send.BulkSendView.as_view(),        name="send-bulk"),

    # ── Phase 3.2 – Messages ─────────────────────────────────────────────────
    path("messages/",           messages.MessageListView.as_view(),   name="message-list"),
    path("messages/<uuid:pk>/", messages.MessageDetailView.as_view(), name="message-detail"),

    # ── Phase 3.4 – Outbound webhook management ───────────────────────────────
    path("webhooks/",     include("apps.webhooks.urls",       namespace="webhooks")),

    # ── Phase 4.3 – Stats (summary + export) ─────────────────────────────────
    path("stats/",        stats.StatsView.as_view(),          name="stats"),
    path("stats/export/", stats.StatsExportView.as_view(),    name="stats-export"),

    # ── Phase 4.3 – Inbound ESP webhooks (no auth) ────────────────────────────
    path("inbound/ses/",  inbound.ses_inbound,                name="inbound-ses"),
    path("inbound/esp/",  inbound.esp_inbound,                name="inbound-esp"),
]