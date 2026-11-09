"""Persistence services for NASA environmental data (Phase 3C).

Business/persistence logic lives here, never in views or tasks:

* :func:`start_fetch_job` — open a fetch-operation record.
* :func:`persist_power_response` — idempotent save of a *server-fetched*
  :class:`PowerResponse`.
* :func:`record_fetch_failure` — close a job as failed with provider details.
* :func:`get_farm_series` — read one farm/parameter time series.

The only accepted input for observation values is a ``PowerResponse`` produced
by :mod:`apps.earth_data.providers.power`. Client-supplied numbers can never be
persisted as NASA data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.earth_data.models import (
    DataFetchJob,
    DatasetSource,
    EnvironmentalObservation,
    Provider,
    TimeStandard,
)
from apps.earth_data.providers.power import (
    COMMUNITY_AGROCLIMATOLOGY,
    TIME_STANDARD_UTC,
    PowerQuery,
    PowerResponse,
)
from apps.farms.models import Farm

logger = logging.getLogger(__name__)

COORDINATE_QUANTUM = Decimal("0.000001")
VALUE_QUANTUM = Decimal("0.0001")
ELEVATION_QUANTUM = Decimal("0.01")
APPROX_FILL_QUANTUM = Decimal("0.001")


class PersistenceError(Exception):
    """Base class for persistence problems (never a provider failure)."""

    code = "persistence_error"


class SourceCatalogueError(PersistenceError):
    """The parameter catalogue has no active row for a requested code."""

    code = "source_catalogue_error"


class JobAlreadyRunning(PersistenceError):
    """A fetch for this farm is already in progress (or was just started)."""

    code = "job_already_running"

    def __init__(self, job: DataFetchJob) -> None:
        super().__init__(f"A fetch job is already running for this farm ({job.pk}).")
        self.job = job


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    """Outcome of saving one POWER response."""

    created_rows: int
    updated_rows: int
    missing_values: int
    days_stored: int
    days_missing: int
    status: str


# ---------------------------------------------------------------------------
# Fetch job lifecycle
# ---------------------------------------------------------------------------


@transaction.atomic
def start_fetch_job(
    *,
    farm: Farm,
    query: PowerQuery,
    requested_by=None,
    geometry_source: str = DataFetchJob.RequestGeometrySource.FARMER_LOCATION,
) -> DataFetchJob:
    """Create a RUNNING fetch-operation record before contacting the provider."""
    if not isinstance(farm, Farm):
        raise TypeError("start_fetch_job requires a Farm instance.")
    if not isinstance(query, PowerQuery):
        raise TypeError("start_fetch_job requires a PowerQuery instance.")

    now = timezone.now()
    fields = {
        "farm": farm,
        "requested_by": requested_by,
        "provider": Provider.NASA_POWER,
        "status": DataFetchJob.Status.RUNNING,
        "started_at": now,
        "requested_start": query.start,
        "requested_end": query.end,
        "parameters": list(query.parameters),
        "requested_longitude": _coordinate(query.longitude),
        "requested_latitude": _coordinate(query.latitude),
        "request_geometry_source": geometry_source,
        "time_standard": TimeStandard.UTC,
        "days_requested": (query.end - query.start).days + 1,
    }

    try:
        # A partial unique constraint allows only one RUNNING job per farm.
        with transaction.atomic():
            return DataFetchJob.objects.create(**fields)
    except IntegrityError:
        running = (
            DataFetchJob.objects.filter(farm=farm, status=DataFetchJob.Status.RUNNING)
            .order_by("-started_at")
            .first()
        )
        if running is None:  # pragma: no cover - only on an unrelated race
            raise
        started = running.started_at or running.created_at
        age_seconds = max(0.0, (now - started).total_seconds())
        stale_after = float(getattr(settings, "NASA_FETCH_STALE_JOB_SECONDS", 1800))
        if age_seconds < stale_after:
            raise JobAlreadyRunning(running) from None

        # A crashed worker left the job RUNNING; retire it and start a new scan.
        DataFetchJob.objects.filter(pk=running.pk, status=DataFetchJob.Status.RUNNING).update(
            status=DataFetchJob.Status.FAILED,
            error_code="stale_job",
            error_message=(
                f"Marked as failed after {int(age_seconds)}s without completion."
            ),
            finished_at=now,
        )
        logger.warning("Retired stale fetch job %s for farm %s", running.pk, farm.pk)
        return DataFetchJob.objects.create(**fields)


@transaction.atomic
def persist_power_response(job: DataFetchJob, response: PowerResponse) -> PersistenceResult:
    """Store a validated POWER response idempotently and close the job.

    Re-importing the same farm/parameter/date updates the existing row instead of
    creating a duplicate, so repeated scans and refreshes are safe.
    """
    if not isinstance(job, DataFetchJob):
        raise TypeError("persist_power_response requires a DataFetchJob instance.")
    if not isinstance(response, PowerResponse):
        raise TypeError(
            "persist_power_response only accepts a PowerResponse from the NASA client; "
            "client-supplied observation values are never stored as NASA data."
        )

    farm = job.farm
    codes = tuple(response.series)
    sources = {
        source.parameter_code: source
        for source in DatasetSource.objects.filter(
            provider=Provider.NASA_POWER,
            community=COMMUNITY_AGROCLIMATOLOGY,
            time_standard=TIME_STANDARD_UTC,
            parameter_code__in=codes,
        )
    }
    unavailable = [code for code in codes if code not in sources or not sources[code].is_active]
    if unavailable:
        raise SourceCatalogueError(
            "No active dataset source for parameter(s): "
            f"{', '.join(sorted(unavailable))}. Run the catalogue migration or reactivate the source."
        )

    now = timezone.now()
    requested_longitude = _coordinate(response.requested_longitude)
    requested_latitude = _coordinate(response.requested_latitude)
    returned_longitude = _coordinate(response.returned_longitude)
    returned_latitude = _coordinate(response.returned_latitude)

    rows: list[EnvironmentalObservation] = []
    missing_values = 0
    days_with_missing: set[date] = set()

    for code, series in response.series.items():
        source = sources[code]
        for observation_date, value in sorted(series.values.items()):
            if value is None:
                missing_values += 1
                days_with_missing.add(observation_date)
            rows.append(
                EnvironmentalObservation(
                    farm=farm,
                    source=source,
                    observation_date=observation_date,
                    value=None if value is None else _value(value),
                    quality_status=(
                        EnvironmentalObservation.QualityStatus.MISSING
                        if value is None
                        else EnvironmentalObservation.QualityStatus.AVAILABLE
                    ),
                    fetch_job=job,
                    requested_longitude=requested_longitude,
                    requested_latitude=requested_latitude,
                    returned_longitude=returned_longitude,
                    returned_latitude=returned_latitude,
                    # bulk_create does not run pre_save, so timestamps are explicit.
                    created_at=now,
                    updated_at=now,
                )
            )

    if rows:
        existing = set(
            EnvironmentalObservation.objects.filter(
                farm=farm,
                source_id__in=[source.pk for source in sources.values()],
                observation_date__gte=min(row.observation_date for row in rows),
                observation_date__lte=max(row.observation_date for row in rows),
            ).values_list("source_id", "observation_date")
        )
        created_rows = sum(1 for row in rows if (row.source_id, row.observation_date) not in existing)
        updated_rows = len(rows) - created_rows

        EnvironmentalObservation.objects.bulk_create(
            rows,
            batch_size=500,
            update_conflicts=True,
            unique_fields=["farm", "source", "observation_date"],
            update_fields=[
                "value",
                "quality_status",
                "fetch_job",
                "requested_longitude",
                "requested_latitude",
                "returned_longitude",
                "returned_latitude",
                "updated_at",
            ],
        )
    else:  # pragma: no cover - a parsed response always carries values
        created_rows = 0
        updated_rows = 0

    days_stored = len({row.observation_date for row in rows})
    days_missing = len(days_with_missing)

    job.returned_longitude = returned_longitude
    job.returned_latitude = returned_latitude
    job.returned_elevation_m = (
        None
        if response.returned_elevation_m is None
        else _quantize(response.returned_elevation_m, ELEVATION_QUANTUM)
    )
    job.api_name = response.api_name[:80]
    job.api_version = response.api_version[:32]
    job.source_products = list(response.sources)
    job.time_standard = response.time_standard
    job.fill_value = _quantize(response.fill_value, APPROX_FILL_QUANTUM)
    job.days_stored = days_stored
    job.days_missing = days_missing
    job.status = (
        DataFetchJob.Status.PARTIALLY_SUCCEEDED
        if missing_values
        else DataFetchJob.Status.SUCCEEDED
    )
    job.finished_at = now
    if job.started_at is not None:
        job.duration_ms = max(0, int((now - job.started_at).total_seconds() * 1000))
    job.save(
        update_fields=[
            "returned_longitude",
            "returned_latitude",
            "returned_elevation_m",
            "api_name",
            "api_version",
            "source_products",
            "time_standard",
            "fill_value",
            "days_stored",
            "days_missing",
            "status",
            "finished_at",
            "duration_ms",
        ]
    )

    return PersistenceResult(
        created_rows=created_rows,
        updated_rows=updated_rows,
        missing_values=missing_values,
        days_stored=days_stored,
        days_missing=days_missing,
        status=job.status,
    )


@transaction.atomic
def record_fetch_failure(
    job: DataFetchJob,
    error: BaseException,
    *,
    duration_ms: int | None = None,
) -> DataFetchJob:
    """Close a job as FAILED, preserving the provider's error code and details."""
    if not isinstance(job, DataFetchJob):
        raise TypeError("record_fetch_failure requires a DataFetchJob instance.")

    now = timezone.now()
    code = getattr(error, "code", None) or "unknown_error"
    message = getattr(error, "message", None) or str(error) or error.__class__.__name__
    details: Iterable[str] = getattr(error, "details", ()) or ()

    job.status = DataFetchJob.Status.FAILED
    job.error_code = str(code)[:64]
    job.error_message = "\n".join([str(message), *[str(item) for item in details]])[:2000]
    job.finished_at = now
    if duration_ms is None and job.started_at is not None:
        duration_ms = max(0, int((now - job.started_at).total_seconds() * 1000))
    if duration_ms is not None:
        job.duration_ms = duration_ms
    job.save(
        update_fields=[
            "status",
            "error_code",
            "error_message",
            "finished_at",
            "duration_ms",
        ]
    )
    return job


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def get_farm_series(
    farm: Farm,
    parameter_code: str,
    *,
    start: date | None = None,
    end: date | None = None,
) -> QuerySet[EnvironmentalObservation]:
    """Daily observations for one farm and parameter, oldest first."""
    queryset = EnvironmentalObservation.objects.filter(
        farm=farm, source__parameter_code=parameter_code
    ).select_related("source", "fetch_job")
    if start is not None:
        queryset = queryset.filter(observation_date__gte=start)
    if end is not None:
        queryset = queryset.filter(observation_date__lte=end)
    return queryset.order_by("observation_date")


def get_farm_observations(
    farm: Farm,
    *,
    codes: Sequence[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> QuerySet[EnvironmentalObservation]:
    """Daily observations for one farm, optionally filtered by parameter and range."""
    queryset = EnvironmentalObservation.objects.filter(farm=farm).select_related("source")
    if codes:
        queryset = queryset.filter(source__parameter_code__in=codes)
    if start is not None:
        queryset = queryset.filter(observation_date__gte=start)
    if end is not None:
        queryset = queryset.filter(observation_date__lte=end)
    return queryset.order_by("observation_date", "source__parameter_code")


# ---------------------------------------------------------------------------
# Conversions
# ---------------------------------------------------------------------------


def _coordinate(value: float | int) -> Decimal:
    return _quantize(value, COORDINATE_QUANTUM)


def _value(value: float) -> Decimal:
    return _quantize(value, VALUE_QUANTUM)


def _quantize(value: float | int | str, quantum: Decimal) -> Decimal:
    try:
        return Decimal(str(value)).quantize(quantum)
    except (InvalidOperation, ValueError) as exc:
        raise PersistenceError(f"Cannot store non-numeric value {value!r}.") from exc


__all__ = [
    "JobAlreadyRunning",
    "PersistenceError",
    "PersistenceResult",
    "SourceCatalogueError",
    "get_farm_observations",
    "get_farm_series",
    "persist_power_response",
    "record_fetch_failure",
    "start_fetch_job",
]
