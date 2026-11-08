"""Farm routes mounted under /api/v1/."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import FarmContextView, FarmViewSet

router = SimpleRouter()
router.register("farms", FarmViewSet, basename="farm")

urlpatterns = [
    path(
        "farms/<int:farm_id>/context/",
        FarmContextView.as_view(),
        name="farm-context",
    ),
    *router.urls,
]
