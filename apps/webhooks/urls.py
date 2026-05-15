"""
Webhook URL routes — mounted at /api/v1/webhooks/ via api/v1/urls.py.
Place: apps/webhooks/urls.py
"""

from django.urls import path
from .views import (
    WebhookListCreateView,
    WebhookDetailView,
    WebhookTestView,
    WebhookDeliveryListView,
)

app_name = "webhooks"

urlpatterns = [
    path("",                        WebhookListCreateView.as_view(),  name="list-create"),
    path("<uuid:pk>/",              WebhookDetailView.as_view(),      name="detail"),
    path("<uuid:pk>/test/",         WebhookTestView.as_view(),        name="test"),
    path("<uuid:pk>/deliveries/",   WebhookDeliveryListView.as_view(), name="deliveries"),
]
