"""Root /api/v1/ routing: health, accounts, farms."""

from django.urls import include, path

from apps.core.views import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.farms.urls")),
]
