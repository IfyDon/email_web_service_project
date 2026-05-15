from django.urls import path, include
from api.v1.views import send, messages

app_name = "v1"

urlpatterns = [
    # Phase 2.1
    path("auth/",         include("apps.authentication.urls", namespace="authentication")),

    # Phase 2.2
    path("domains/",      include("apps.domains.urls",        namespace="domains")),

    # Phase 2.3
    path("templates/",    include("apps.templates_app.urls",  namespace="templates_app")),

    # Phase 2.4
    path("suppressions/", include("apps.suppressions.urls",   namespace="suppressions")),

    # Phase 3.1
    path("send",               send.SendView.as_view(),             name="send"),
    path("send/bulk",          send.BulkSendView.as_view(),         name="send-bulk"),

    # Phase 3.2
    path("messages/",          messages.MessageListView.as_view(),  name="message-list"),
    path("messages/<uuid:pk>/",messages.MessageDetailView.as_view(),name="message-detail"),
]