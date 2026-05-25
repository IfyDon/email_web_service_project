"""
Version-1 API URL registry.

"""

from django.urls import path, include
from api.v1.views import send, messages, stats

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

    # ── Phase 3.1 – Email send (single + bulk) ────────────────────────────────
    path("send",          send.SendView.as_view(),            name="send"),
    path("send/bulk",     send.BulkSendView.as_view(),        name="send-bulk"),

    # ── Phase 3.2 – Message list & detail ────────────────────────────────────
    path("messages/",           messages.MessageListView.as_view(),   name="message-list"),
    path("messages/<uuid:pk>/", messages.MessageDetailView.as_view(), name="message-detail"),

    # ── Phase 3.4 – Webhook management ───────────────────────────────────────
    path("webhooks/",    include("apps.webhooks.urls",        namespace="webhooks")),

    # ── Phase 4.2 – Stats ─────────────────────────────────────────────────────
    path("stats/",        stats.StatsView.as_view(),          name="stats"),
]