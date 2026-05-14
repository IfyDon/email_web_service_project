from django.urls import path
from .views import SuppressionListCreateView, SuppressionDetailView, SuppressionCheckView

app_name = "suppressions"

urlpatterns = [
    path("",             SuppressionListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/",   SuppressionDetailView.as_view(),    name="detail"),
    path("check/",       SuppressionCheckView.as_view(),     name="check"),
]