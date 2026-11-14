"""Root /api/v1/ routing: health, accounts, farms, environmental data."""

from django.urls import include, path

from apps.core.views import HealthCheckView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("", include("apps.accounts.urls")),
    # Phase 3E routes are declared before the farms router so the more specific
    # farm sub-paths win during resolution.
    path("", include("apps.earth_data.urls")),
    path("", include("apps.indicators.urls")),
    path("", include("apps.agronomy.urls")),
    path("", include("apps.simulations.urls")),
    path("", include("apps.farms.urls")),
]
