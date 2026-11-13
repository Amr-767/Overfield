"""Environmental summary API (Phase 4D).

``GET /api/v1/farms/{farm_id}/environment/current/``

Owner-scoped like every other farm endpoint: another farmer's farm is a 404.
The view is thin — validation and orchestration live in the serializer and
:mod:`apps.indicators.summary`.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.farms.models import Farm
from apps.farms.permissions import IsFarmOwner

from .coverage import default_window_days, max_window_days
from .summary import build_environment_summary


class SummaryQuerySerializer(serializers.Serializer):
    """Query parameters for the summary endpoint."""

    window_days = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Analysis window in days (1–366, default 30).",
    )

    def validate_window_days(self, value: int | None) -> int:
        if value is None:
            return default_window_days()
        limit = max_window_days()
        if value > limit:
            raise serializers.ValidationError(
                f"window_days must be between 1 and {limit}."
            )
        return value


class FarmEnvironmentCurrentView(generics.GenericAPIView):
    """GET /api/v1/farms/{farm_id}/environment/current/"""

    permission_classes = [IsAuthenticated, IsFarmOwner]

    def get(self, request: Request, farm_id: int) -> Response:
        farm = get_object_or_404(Farm, pk=farm_id, owner=request.user)
        self.check_object_permissions(request, farm)

        query = SummaryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        window_days = query.validated_data.get("window_days", default_window_days())
        summary = build_environment_summary(farm, window_days=window_days)
        return Response(summary.as_dict(), status=status.HTTP_200_OK)


__all__ = ["FarmEnvironmentCurrentView", "SummaryQuerySerializer"]
