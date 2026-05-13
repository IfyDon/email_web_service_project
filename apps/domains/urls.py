"""
Domain URL routes — mounted at /api/v1/domains/ via api/v1/urls.py.

Place: apps/domains/urls.py
"""

from django.urls import path
from .views import DomainListCreateView, DomainDetailView, DomainVerifyView

app_name = "domains"

urlpatterns = [
    path("",              DomainListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/",    DomainDetailView.as_view(),     name="detail"),
    path("<uuid:pk>/verify/", DomainVerifyView.as_view(), name="verify"),
]