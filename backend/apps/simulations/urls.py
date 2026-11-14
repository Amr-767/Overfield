"""Scenario simulation routes mounted under /api/v1/ (Phase 6.3)."""

from django.urls import path

from .views import FarmSimulationView, SimulationDetailView, SimulationStepsView

urlpatterns = [
    path(
        "farms/<int:farm_id>/simulations/",
        FarmSimulationView.as_view(),
        name="farm-simulations",
    ),
    path(
        "simulations/<uuid:simulation_id>/",
        SimulationDetailView.as_view(),
        name="simulation-detail",
    ),
    path(
        "simulations/<uuid:simulation_id>/steps/",
        SimulationStepsView.as_view(),
        name="simulation-steps",
    ),
]
