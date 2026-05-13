from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # OpenAPI schema + interactive docs
    path("api/schema/", SpectacularAPIView.as_view(),                          name="schema"),
    path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"),     name="swagger-ui"),
    path("api/redoc/",  SpectacularRedocView.as_view(url_name="schema"),       name="redoc"),

    # REST API
    path("api/", include("api.urls")),

    # Tracking pixel endpoints
    path("t/", include("tracking.urls")),

    # Django Allauth
    path("accounts/", include("allauth.urls")),

    # Web dashboard
    path("", include("web.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass