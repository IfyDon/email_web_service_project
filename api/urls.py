# ══════════════════════════════════════════════════════════════════════════════
# api/urls.py  – top-level API router
# ══════════════════════════════════════════════════════════════════════════════

from django.urls import path, include
from .views import health_check, api_root

app_name = "api"

urlpatterns = [
    # Discovery & health
    path("",         api_root,     name="root"),
    path("health/",  health_check, name="health"),

    # Versioned routes
    path("v1/", include("api.v1.urls", namespace="v1")),
]
