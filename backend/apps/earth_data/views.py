"""Environmental data API (Phase 3E).

Three owner-scoped endpoints:

* ``GET  /api/v1/farms/{farm_id}/environment/daily/`` — paginated observations.
* ``POST /api/v1/farms/{farm_id}/scans/`` — queue a POWER refresh (202).
* ``GET  /api/v1/data-jobs/{job_id}/`` — status of one fetch operation.

Every farm lookup is filtered by ``owner=request.user`` so another farmer's farm
is a 404, never a 403 that would confirm it exists.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.earth_data.ingestion import default_date_range, plan_farm_fetch
from apps.earth_data.models import DataFetchJob, EnvironmentalObservation, Provider
from apps.earth_data.providers.power import RECOMMENDED_PARAMETERS
from apps.earth_data.serializers import (
    DataJobSerializer,
    ObservationQuerySerializer,
    ObservationSerializer,
    ScanRequestSerializer,
)
from apps.earth_data.services import PersistenceError, record_fetch_failure
from apps.earth_data.tasks import enqueue_farm_fetch
from apps.earth_data.validation import (
    active_sources,
    normalise_parameters,
    validate_date_range,
    validate_parameters,
)
from apps.farms.models import Farm
from apps.farms.permissions import IsFarmOwner

logger = logging.getLogger(__name__)

SPATIAL_NOTE = (
    "Values are provider grid-cell estimates for the farm's representative point, "
    "not on-farm measurements."
)


class FarmScopedView(generics.GenericAPIView):
    """Shared owner-scoped farm lookup."""

    permission_classes = [IsAuthenticated, IsFarmOwner]

    def get_farm(self, request: Request, farm_id: int) -> Farm:
        farm = get_object_or_404(Farm, pk=farm_id, owner=request.user)
        self.check_object_permissions(request, farm)
        return farm


class FarmObservationsView(FarmScopedView):
    """GET /api/v1/farms/{farm_id}/environment/daily/"""

    pagination_class = PageNumberPagination

    def get(self, request: Request, farm_id: int) -> Response:
        farm = self.get_farm(request, farm_id)

        query = ObservationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        default_start, default_end = default_date_range()
        start = query.validated_data.get("start") or default_start
        end = query.validated_data.get("end") or default_end

        codes = normalise_parameters(request.query_params.getlist("parameter"))
        codes = validate_parameters(codes or RECOMMENDED_PARAMETERS)
        start, end = validate_date_range(start, end, parameters=codes)

        queryset = (
            EnvironmentalObservation.objects.filter(
                farm=farm,
                observation_date__gte=start,
                observation_date__lte=end,
                source__parameter_code__in=codes,
            )
            .select_related("source")
            .order_by("observation_date", "source__parameter_code")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            results = ObservationSerializer(page, many=True).data
            total = self.paginator.page.paginator.count
            next_link = self.paginator.get_next_link()
            previous_link = self.paginator.get_previous_link()
        else:  # pragma: no cover - pagination is always configured
            results = ObservationSerializer(list(queryset), many=True).data
            total = len(results)
            next_link = previous_link = None

        sources = active_sources()
        return Response(
            {
                "farm_id": farm.id,
                "count": total,
                "next": next_link,
                "previous": previous_link,
                "range": {"start": start.isoformat(), "end": end.isoformat()},
                "parameters": [
                    {
                        "code": code,
                        "units": sources[code].units,
                        "long_name": sources[code].long_name,
                        "product": sources[code].product,
                        "daily_aggregation": sources[code].daily_aggregation,
                        "data_category": sources[code].data_category,
                        "first_available_date": sources[code].first_available_date.isoformat(),
                    }
                    for code in codes
                    if code in sources
                ],
                "spatial": _spatial_metadata(queryset.order_by("-observation_date").first()),
                "results": results,
            }
        )


class FarmScanView(FarmScopedView):
    """POST /api/v1/farms/{farm_id}/scans/"""

    def post(self, request: Request, farm_id: int) -> Response:
        farm = self.get_farm(request, farm_id)

        payload = ScanRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        default_start, default_end = default_date_range()
        start = payload.validated_data.get("start") or default_start
        end = payload.validated_data.get("end") or default_end
        force = bool(payload.validated_data.get("force", False))

        codes = normalise_parameters(payload.validated_data.get("parameters"))
        codes = validate_parameters(codes or RECOMMENDED_PARAMETERS)
        start, end = validate_date_range(start, end, parameters=codes)

        try:
            plan = plan_farm_fetch(
                farm=farm,
                start=start,
                end=end,
                parameters=codes,
                force=force,
                requested_by=request.user,
            )
        except PersistenceError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        if plan.status == "already_running":
            job_id = plan.existing_job_id
            return Response(
                {
                    "status": "already_running",
                    "farm_id": farm.id,
                    "job_id": job_id,
                    "detail": "A scan is already running for this farm.",
                    "status_url": f"/api/v1/data-jobs/{job_id}/",
                },
                status=status.HTTP_409_CONFLICT,
            )

        if plan.status == "already_current":
            return Response(
                {
                    "status": "already_current",
                    "farm_id": farm.id,
                    "start": plan.start.isoformat(),
                    "end": plan.end.isoformat(),
                    "parameters": list(codes),
                    "detail": "All requested days already have data. Use force=true to refresh.",
                },
                status=status.HTTP_200_OK,
            )

        job = plan.job
        if job is None:  # pragma: no cover - defensive
            return Response(
                {"detail": "The scan could not be prepared."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            task_id = enqueue_farm_fetch(
                farm=farm,
                start=plan.start,
                end=plan.end,
                requested_by=request.user,
                force=True,
                fetch_job_id=str(job.pk),
            )
        except Exception as exc:  # broker down, serialization problem, ...
            record_fetch_failure(job, exc)
            logger.exception("Could not enqueue NASA ingestion for farm %s", farm.id)
            return Response(
                {
                    "detail": "The background worker is unavailable; the scan was not queued.",
                    "job_id": str(job.pk),
                    "status": "failed",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        logger.info("Queued NASA scan %s for farm %s (task %s)", job.pk, farm.id, task_id)
        return Response(
            {
                "status": "QUEUED",
                "farm_id": farm.id,
                "job_id": str(job.pk),
                "task_id": task_id,
                "start": plan.start.isoformat(),
                "end": plan.end.isoformat(),
                "parameters": list(codes),
                "status_url": f"/api/v1/data-jobs/{job.pk}/",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class DataJobDetailView(generics.RetrieveAPIView):
    """GET /api/v1/data-jobs/{job_id}/"""

    serializer_class = DataJobSerializer
    permission_classes = [IsAuthenticated, IsFarmOwner]
    lookup_url_kwarg = "job_id"

    def get_queryset(self):
        return DataFetchJob.objects.select_related("farm").filter(
            farm__owner=self.request.user, provider=Provider.NASA_POWER
        )


def _spatial_metadata(sample: EnvironmentalObservation | None) -> dict | None:
    """Describe where the values came from, without exposing raw payloads."""
    if sample is None:
        return None

    requested = {
        "longitude": str(sample.requested_longitude),
        "latitude": str(sample.requested_latitude),
    }
    returned = None
    if sample.returned_longitude is not None and sample.returned_latitude is not None:
        returned = {
            "longitude": str(sample.returned_longitude),
            "latitude": str(sample.returned_latitude),
        }

    return {
        "requested": requested,
        "returned": returned,
        "time_standard": sample.source.time_standard,
        "native_resolution_note": sample.source.native_resolution_note or None,
        "note": SPATIAL_NOTE,
    }


__all__ = ["DataJobDetailView", "FarmObservationsView", "FarmScanView"]
