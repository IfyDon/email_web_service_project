"""
Tracking URL routes — mounted at /t/ by config/urls.py.

Keep these URLs as short as possible to minimise email body size.

  /t/o/<token>/  → open pixel
  /t/c/<token>/  → click redirect

Place: tracking/urls.py
"""

from django.urls import path
from . import views

app_name = "tracking"

urlpatterns = [
    path("o/<str:token>/", views.open_pixel,    name="open-pixel"),
    path("c/<str:token>/", views.click_redirect, name="click-redirect"),
]