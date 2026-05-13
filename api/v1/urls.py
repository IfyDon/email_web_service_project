# ══════════════════════════════════════════════════════════════════════════════
# api/v1/urls.py  – version-1 endpoint registry
# ══════════════════════════════════════════════════════════════════════════════
# NOTE: save this block in api/v1/urls.py (separate file)
"""
from django.urls import path
from api.v1.views import send, messages, domains, templates

app_name = "v1"

urlpatterns = [
    # Send
    path("send",            send.SendView.as_view(),      name="send"),
    path("send/bulk",       send.BulkSendView.as_view(),  name="send-bulk"),

    # Messages
    path("messages",        messages.MessageListView.as_view(),   name="message-list"),
    path("messages/<uuid:pk>", messages.MessageDetailView.as_view(), name="message-detail"),

    # Templates
    path("templates",          templates.TemplateListCreateView.as_view(), name="template-list"),
    path("templates/<uuid:pk>", templates.TemplateDetailView.as_view(),    name="template-detail"),

    # Domains
    path("domains",                 domains.DomainListCreateView.as_view(), name="domain-list"),
    path("domains/<uuid:pk>",       domains.DomainDetailView.as_view(),     name="domain-detail"),
    path("domains/<uuid:pk>/verify", domains.DomainVerifyView.as_view(),    name="domain-verify"),

    # Stats & Webhooks  (Phase 4)
    # path("stats",    stats.StatsView.as_view(),          name="stats"),
    # path("webhooks", webhooks.WebhookListCreateView.as_view(), name="webhook-list"),
    # path("webhooks/<uuid:pk>", webhooks.WebhookDetailView.as_view(), name="webhook-detail"),
]
"""
# Uncomment the block above and place it in api/v1/urls.py once Phase 4 begins.
# For Phase 1 we just register an empty urlconf to avoid import errors.

from django.urls import path, include

app_name = "v1"
urlpatterns: list = [
    # ── Auth & API key management (Phase 2.1) ─────────────────────────────────
    path("auth/", include("apps.authentication.urls", namespace="authentication")),

    # ── Domain verification (Phase 2.2) ───────────────────────────────────────
    path("domains/", include("apps.domains.urls", namespace="domains")),

    # ── Phase 2.3 onwards (uncomment as implemented) ──────────────────────────
    # path("templates/", include("apps.templates_app.urls", namespace="templates")),

    # ── Phase 3 (uncomment as implemented) ────────────────────────────────────
    # path("send",               send.SendView.as_view(),              name="send"),
    # path("send/bulk",          send.BulkSendView.as_view(),          name="send-bulk"),
    # path("messages/",          include("apps.email_messages.urls",   namespace="messages")),
    # path("stats/",             stats.StatsView.as_view(),            name="stats"),
    # path("webhooks/",          include("apps.webhooks.urls",
]