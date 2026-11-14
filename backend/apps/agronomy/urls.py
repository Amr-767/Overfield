from django.urls import path

from .review_api import ReviewEvidenceView
from .rotation_api import (
    FarmRecommendationCreateView,
    RecommendationCompareView,
    RecommendationDetailView,
    RecommendationExplanationView,
)
from .views import CropCalendarView, CropListView, CropProfileView

urlpatterns = [
    path("agronomy/reviews/", ReviewEvidenceView.as_view(), name="agronomy-evidence-review"),
    path("farms/<int:farm_id>/recommendations/", FarmRecommendationCreateView.as_view(), name="recommendation-create"),
    path("recommendations/<uuid:recommendation_id>/", RecommendationDetailView.as_view(), name="recommendation-detail"),
    path("recommendations/<uuid:recommendation_id>/compare/", RecommendationCompareView.as_view(), name="recommendation-compare"),
    path("recommendations/<uuid:recommendation_id>/explanation/", RecommendationExplanationView.as_view(), name="recommendation-explanation"),
    path("regions/<str:region_code>/crop-calendar/", CropCalendarView.as_view(), name="crop-calendar"),
    path("crops/", CropListView.as_view(), name="crop-list"),
    path("crops/<int:crop_id>/profiles/", CropProfileView.as_view(), name="crop-profile"),
]
