from django.urls import path, include

app_name = "v1"

urlpatterns = [
    # Phase 2.1 – Auth & API key management
    path("auth/",         include("apps.authentication.urls", namespace="authentication")),
    # Phase 2.2 – Domain verification
    path("domains/",      include("apps.domains.urls",        namespace="domains")),
    # Phase 2.3 – Email templates
    path("templates/",    include("apps.templates_app.urls",  namespace="templates_app")),
    # Phase 2.4 – Suppression list
    path("suppressions/", include("apps.suppressions.urls",   namespace="suppressions")),

    # Phase 3+ (uncomment as implemented)
    # path("send",          send.SendView.as_view(),            name="send"),
    # path("send/bulk",     send.BulkSendView.as_view(),        name="send-bulk"),
    # path("messages/",     include("apps.email_messages.urls", namespace="messages")),
    # path("stats/",        stats.StatsView.as_view(),          name="stats"),
    # path("webhooks/",     include("apps.webhooks.urls",       namespace="webhooks")),
]