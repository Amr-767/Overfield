"""Environmental data routes mounted under /api/v1/ (Phase 3E)."""

from django.urls import path

from .views import DataJobDetailView, FarmObservationsView, FarmScanView

urlpatterns = [
    path(
        "farms/<int:farm_id>/environment/daily/",
        FarmObservationsView.as_view(),
        name="farm-environment-daily",
    ),
    path(
        "farms/<int:farm_id>/scans/",
        FarmScanView.as_view(),
        name="farm-scan",
    ),
    path(
        "data-jobs/<uuid:job_id>/",
        DataJobDetailView.as_view(),
        name="data-job-detail",
    ),
]
