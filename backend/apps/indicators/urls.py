"""Indicator routes mounted under /api/v1/ (Phase 4D)."""

from django.urls import path

from .views import FarmEnvironmentCurrentView

urlpatterns = [
    path(
        "farms/<int:farm_id>/environment/current/",
        FarmEnvironmentCurrentView.as_view(),
        name="farm-environment-current",
    ),
]
