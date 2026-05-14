"""
Template URL routes — mounted at /api/v1/templates/ via api/v1/urls.py
Place: apps/templates_app/urls.py
"""

from django.urls import path
from .views import (
    TemplateListCreateView,
    TemplateDetailView,
    TemplatePreviewView,
    TemplateVersionListView,
    TemplateRestoreView,
)

app_name = "templates_app"

urlpatterns = [
    path("",                         TemplateListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/",               TemplateDetailView.as_view(),     name="detail"),
    path("<uuid:pk>/preview/",       TemplatePreviewView.as_view(),    name="preview"),
    path("<uuid:pk>/versions/",      TemplateVersionListView.as_view(),name="versions"),
    path("<uuid:pk>/restore/",       TemplateRestoreView.as_view(),    name="restore"),
]

