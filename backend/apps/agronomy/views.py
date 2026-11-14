from django.db.models import Prefetch, Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AgriculturalDataset, Crop, CropCharacteristic, GeographicApplicability, RegionAgronomyProfile
from .serializers import CropListSerializer, CropProfileSerializer


class CropListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CropListSerializer

    def get_queryset(self):
        region = self.request.query_params.get("region_code")
        if not region:
            raise ValidationError({"region_code": ["This query parameter is required."]})
        # Only reviewer-approved evidence is region-ready. A source may claim
        # GENERAL/DIRECT applicability and a validation status, but those claims
        # are never a substitute for the independent review decision.
        return Crop.objects.filter(
            Q(characteristics__approved_geographic_applicability__in=[
                GeographicApplicability.GENERAL,
                GeographicApplicability.TRANSFERABLE_LIMITED,
            ])
            | Q(
                characteristics__approved_geographic_applicability=GeographicApplicability.DIRECT,
                characteristics__geographic_scope__iexact=region,
            ),
            characteristics__approval_status="APPROVED",
            characteristics__validation_status="VALID",
            characteristics__original_value__isnull=False,
            characteristics__dataset__status="APPROVED",
            characteristics__dataset_import__status="SUCCEEDED",
        ).distinct().prefetch_related(
            Prefetch("characteristics", queryset=CropCharacteristic.objects.select_related("dataset", "dataset_import"))
        )


class CropCalendarView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, region_code: str):
        profile = RegionAgronomyProfile.objects.filter(
            region_code__iexact=region_code,
            status=AgriculturalDataset.Status.APPROVED,
        ).prefetch_related("seasons__crop_windows__crop").order_by("-calendar_version").first()
        if profile is None:
            from django.http import Http404
            raise Http404
        seasons = []
        for season in profile.seasons.all():
            seasons.append({
                "season_code": season.season_code,
                "label": season.label,
                "start_month_day": season.start_month_day,
                "end_month_day": season.end_month_day,
                "evidence_ids": [season.evidence_reference],
                "crops": [
                    {"crop_code": window.crop.code,
                     "planting_window": window.planting_window or None,
                     "harvest_window": window.harvest_window or None,
                     "evidence_ids": [window.evidence_reference]}
                    for window in season.crop_windows.all()
                ],
            })
        return Response({
            "region_code": profile.region_code,
            "country_code": profile.country_code,
            "timezone": profile.timezone,
            "calendar_version": profile.calendar_version,
            "source": {"title": profile.source_title or None, "publisher": profile.source_publisher or None,
                       "url": profile.source_url or None, "evidence_reference": profile.evidence_reference or None},
            "seasons": seasons,
        })


class CropProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CropProfileSerializer
    lookup_url_kwarg = "crop_id"
    queryset = Crop.objects.prefetch_related(
        Prefetch("characteristics", queryset=CropCharacteristic.objects.select_related("dataset", "dataset_import"))
    )
