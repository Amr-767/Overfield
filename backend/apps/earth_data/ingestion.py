"""Ingestion helpers: coordinates, date ranges and refresh planning (Phase 3D).

Pure-ish helpers kept out of the Celery task and out of any view:

* :func:`resolve_farm_point` — the approved Phase 3A coordinate strategy.
* :func:`default_date_range` — bounded default window (no full-history fetches).
* :func:`pending_date_range` — the smallest range still missing data, so a
  refresh does not re-download years of history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings

from apps.earth_data.models import DataFetchJob, EnvironmentalObservation
from apps.earth_data.providers.power import RECOMMENDED_PARAMETERS, PowerQuery
from apps.earth_data.services import JobAlreadyRunning, PersistenceError, start_fetch_job
from apps.farms.models import Farm


@dataclass(frozen=True, slots=True)
class FarmPoint:
    """Where we ask NASA for data, and why."""

    longitude: float
    latitude: float
    geometry_source: str


def resolve_farm_point(farm: Farm) -> FarmPoint:
    """Return a representative point that lies on the farm.

    * boundary farms → ``ST_PointOnSurface`` of the **largest** part, which is
      guaranteed to be inside the farm (a centroid is not, for concave or
      multi-part fields);
    * location-only farms → the farmer's registered point, unchanged.

    The rule actually used is returned as ``geometry_source`` and stored on the
    fetch job, so provenance is explicit.
    """
    boundary = farm.boundary
    if boundary is not None:
        parts = list(boundary) if boundary.geom_type == "MultiPolygon" else [boundary]
        parts = [part for part in parts if not part.empty]
        if parts:
            largest = max(parts, key=lambda part: part.area)
            point = largest.point_on_surface
            return FarmPoint(
                longitude=float(point.x),
                latitude=float(point.y),
                geometry_source=DataFetchJob.RequestGeometrySource.POINT_ON_SURFACE,
            )

    if farm.location is not None:
        return FarmPoint(
            longitude=float(farm.location.x),
            latitude=float(farm.location.y),
            geometry_source=DataFetchJob.RequestGeometrySource.FARMER_LOCATION,
        )

    raise PersistenceError(
        f"Farm {farm.pk} has neither a boundary nor a location; cannot resolve a NASA request point."
    )


def default_date_range(today: date | None = None) -> tuple[date, date]:
    """Default window: a bounded history ending before the NRT latency gap.

    POWER near-real-time data lags by ~2 days, so the window ends
    ``NASA_FETCH_LATENCY_DAYS`` before today and never covers the full archive.
    """
    days = int(getattr(settings, "NASA_FETCH_DEFAULT_DAYS", 365))
    latency = int(getattr(settings, "NASA_FETCH_LATENCY_DAYS", 3))
    end = (today or date.today()) - timedelta(days=latency)
    start = end - timedelta(days=max(1, days) - 1)
    return start, end


def pending_date_range(
    farm: Farm,
    start: date,
    end: date,
    parameters: tuple[str, ...],
) -> tuple[date, date] | None:
    """Smallest contiguous range that still lacks at least one parameter value.

    Returns ``None`` when every date in ``[start, end]`` already has an
    ``AVAILABLE`` observation for every requested parameter, so a repeat scan
    performs no HTTP request at all.
    """
    rows = (
        EnvironmentalObservation.objects.filter(
            farm=farm,
            observation_date__gte=start,
            observation_date__lte=end,
            source__parameter_code__in=parameters,
            quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
        )
        .values_list("observation_date", "source__parameter_code")
        .distinct()
    )

    have: dict[date, set[str]] = {}
    for observation_date, parameter_code in rows:
        have.setdefault(observation_date, set()).add(parameter_code)

    expected = len(set(parameters))
    missing_days: list[date] = []
    current = start
    while current <= end:
        if len(have.get(current, set())) < expected:
            missing_days.append(current)
        current += timedelta(days=1)

    if not missing_days:
        return None
    return missing_days[0], missing_days[-1]


@dataclass(frozen=True, slots=True)
class FetchPlan:
    """Outcome of planning one scan, shared by the API and the Celery task."""

    status: str  # "ready" | "already_current" | "already_running"
    start: date
    end: date
    geometry_source: str = ""
    job: DataFetchJob | None = None
    query: PowerQuery | None = None
    existing_job_id: str | None = None


def plan_farm_fetch(
    *,
    farm: Farm,
    start: date,
    end: date,
    parameters: tuple[str, ...] = RECOMMENDED_PARAMETERS,
    force: bool = False,
    requested_by=None,
) -> FetchPlan:
    """Resolve the point, trim the window to missing days and open a fetch job.

    Returns ``status="already_current"`` when every requested day already has
    data (so no provider request is made), or ``"already_running"`` when another
    scan for this farm holds the single RUNNING slot.
    """
    point = resolve_farm_point(farm)

    effective_start, effective_end = start, end
    if not force:
        pending = pending_date_range(farm, start, end, parameters)
        if pending is None:
            return FetchPlan(
                status="already_current",
                start=start,
                end=end,
                geometry_source=point.geometry_source,
            )
        effective_start, effective_end = pending

    query = PowerQuery(
        latitude=point.latitude,
        longitude=point.longitude,
        start=effective_start,
        end=effective_end,
        parameters=parameters,
    )

    try:
        job = start_fetch_job(
            farm=farm,
            query=query,
            requested_by=requested_by,
            geometry_source=point.geometry_source,
        )
    except JobAlreadyRunning as exc:
        return FetchPlan(
            status="already_running",
            start=start,
            end=end,
            geometry_source=point.geometry_source,
            existing_job_id=str(exc.job.pk),
        )

    return FetchPlan(
        status="ready",
        start=effective_start,
        end=effective_end,
        geometry_source=point.geometry_source,
        job=job,
        query=query,
    )


__all__ = [
    "FarmPoint",
    "FetchPlan",
    "default_date_range",
    "pending_date_range",
    "plan_farm_fetch",
    "resolve_farm_point",
]
