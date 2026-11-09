"""Celery tasks for NASA POWER ingestion (Phase 3D).

The task is the only place that combines the three existing pieces:

* :func:`apps.earth_data.providers.get_power_client` — Phase 3B HTTP client;
* :func:`apps.earth_data.ingestion.resolve_farm_point` — coordinate strategy;
* :func:`apps.earth_data.services.persist_power_response` — Phase 3C storage.

Design decisions
----------------
* **Bounded retries**: only :class:`PowerTransientError` is retried, with
  exponential backoff and ``max_retries`` from settings. Permanent provider
  errors (4xx / malformed payload / bad configuration) fail immediately.
* **One job row per scan**: the retry receives ``fetch_job_id`` so retries
  refine the same ``DataFetchJob`` instead of flooding the history.
* **A failed request never writes observations**: persistence only happens
  after a fully validated response, so existing data is untouched on failure.
* **No HTTP in a request handler**: callers enqueue with
  :func:`enqueue_farm_fetch` and return immediately.
* **No schedule and no startup fan-out**: nothing is registered in beat and no
  model signal triggers a fetch. The task is ready for a future API trigger.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from celery import shared_task
from django.conf import settings

from apps.earth_data.exceptions import PowerError, PowerTransientError
from apps.earth_data.ingestion import (
    default_date_range,
    plan_farm_fetch,
)
from apps.earth_data.models import DataFetchJob
from apps.earth_data.providers import get_power_client
from apps.earth_data.providers.power import RECOMMENDED_PARAMETERS, PowerQuery
from apps.earth_data.services import (
    JobAlreadyRunning,
    PersistenceError,
    persist_power_response,
    record_fetch_failure,
    start_fetch_job,
)
from apps.farms.models import Farm

logger = logging.getLogger(__name__)

TASK_NAME = "earth_data.ingest_farm_environment"

#: Defaults mirror settings; the task re-reads settings at runtime so tests and
#: deployments can change limits without editing the decorator.
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 5
DEFAULT_RATE_LIMIT = "12/m"
DEFAULT_SOFT_TIME_LIMIT = 300
DEFAULT_TIME_LIMIT = 360


def _config(name: str, fallback: Any) -> Any:
    return getattr(settings, name, fallback)


@shared_task(
    bind=True,
    name=TASK_NAME,
    max_retries=DEFAULT_MAX_RETRIES,
    rate_limit=str(getattr(settings, "NASA_POWER_TASK_RATE_LIMIT", DEFAULT_RATE_LIMIT)),
    soft_time_limit=int(getattr(settings, "NASA_POWER_TASK_SOFT_TIME_LIMIT", DEFAULT_SOFT_TIME_LIMIT)),
    time_limit=int(getattr(settings, "NASA_POWER_TASK_TIME_LIMIT", DEFAULT_TIME_LIMIT)),
    ignore_result=False,
)
def ingest_farm_environment(
    self,
    farm_id: int,
    start: str | None = None,
    end: str | None = None,
    requested_by_id: int | None = None,
    force: bool = False,
    fetch_job_id: str | None = None,
) -> dict[str, Any]:
    """Fetch and store NASA POWER daily data for one farm.

    Returns a JSON-serialisable summary; ``status`` is one of
    ``SUCCEEDED``, ``PARTIALLY_SUCCEEDED``, ``already_current``,
    ``already_running``, ``farm_not_found``, ``invalid_range``,
    ``invalid_farm_geometry`` or ``failed``.
    """
    farm = Farm.objects.filter(pk=farm_id).first()
    if farm is None:
        logger.warning("NASA ingestion requested for a farm that no longer exists: %s", farm_id)
        return {"status": "farm_not_found", "farm_id": farm_id}

    try:
        start_date, end_date = _resolve_range(start, end)
    except ValueError as exc:
        logger.warning("NASA ingestion rejected an invalid date range for farm %s: %s", farm.id, exc)
        return {"status": "invalid_range", "farm_id": farm.id, "error": str(exc)}

    job: DataFetchJob | None = None

    if fetch_job_id:
        # Retry (or API-created job): keep the original coordinates and range.
        job = DataFetchJob.objects.filter(pk=fetch_job_id, farm=farm).first()

    if job is not None:
        query = PowerQuery(
            latitude=float(job.requested_latitude),
            longitude=float(job.requested_longitude),
            start=job.requested_start,
            end=job.requested_end,
            parameters=tuple(job.parameters) or RECOMMENDED_PARAMETERS,
        )
        geometry_source = job.request_geometry_source
    else:
        try:
            plan = plan_farm_fetch(
                farm=farm,
                start=start_date,
                end=end_date,
                force=force,
                requested_by=_requested_by(requested_by_id),
            )
        except PersistenceError as exc:
            logger.warning("Farm %s has no usable geometry: %s", farm.id, exc)
            return {"status": "invalid_farm_geometry", "farm_id": farm.id, "error": str(exc)}

        if plan.status == "already_current":
            logger.info("Farm %s already has all requested data; no request made.", farm.id)
            return {
                "status": "already_current",
                "farm_id": farm.id,
                "start": plan.start.isoformat(),
                "end": plan.end.isoformat(),
                "parameters": list(RECOMMENDED_PARAMETERS),
            }

        if plan.status == "already_running":
            logger.info(
                "Duplicate scan ignored for farm %s: job %s is already running.",
                farm.id,
                plan.existing_job_id,
            )
            return {
                "status": "already_running",
                "farm_id": farm.id,
                "job_id": plan.existing_job_id,
                "existing_status": DataFetchJob.Status.RUNNING,
            }

        job = plan.job
        query = plan.query
        geometry_source = plan.geometry_source

    if job is None or query is None:  # pragma: no cover - defensive
        raise RuntimeError("Fetch planning produced no job/query.")

    logger.info(
        "Fetching NASA POWER for farm %s (job %s): %s..%s at %.5f,%.5f (%s)",
        farm.id,
        job.pk,
        query.start,
        query.end,
        query.latitude,
        query.longitude,
        geometry_source,
    )

    try:
        response = get_power_client().fetch(query)
        result = persist_power_response(job, response)
    except PowerError as exc:
        return _handle_power_failure(self, exc, job, farm, query)
    except Exception as exc:  # noqa: BLE001 - record, then let Celery report FAILURE
        record_fetch_failure(job, exc)
        logger.exception("Unexpected failure during NASA ingestion for farm %s (job %s)", farm.id, job.pk)
        raise

    logger.info(
        "NASA ingestion for farm %s finished: %s created, %s updated, %s missing values (%s days)",
        farm.id,
        result.created_rows,
        result.updated_rows,
        result.missing_values,
        result.days_stored,
    )

    return {
        "status": result.status,
        "farm_id": farm.id,
        "job_id": str(job.pk),
        "created_rows": result.created_rows,
        "updated_rows": result.updated_rows,
        "missing_values": result.missing_values,
        "days_stored": result.days_stored,
        "days_missing": result.days_missing,
        "parameters": list(query.parameters),
        "start": query.start.isoformat(),
        "end": query.end.isoformat(),
        "coordinates": {
            "requested": [float(query.longitude), float(query.latitude)],
            "geometry_source": geometry_source,
        },
    }


def enqueue_farm_fetch(
    *,
    farm: Farm | int,
    start: date | str | None = None,
    end: date | str | None = None,
    requested_by=None,
    force: bool = False,
    countdown: int = 0,
    fetch_job_id: str | None = None,
) -> str:
    """Queue a farm scan and return the Celery task id immediately.

    This is the integration point for a future REST endpoint or a scheduler; it
    performs no HTTP work itself and is not called from any model signal.
    """
    farm_id = farm.pk if isinstance(farm, Farm) else int(farm)
    requested_by_id = getattr(requested_by, "pk", None)
    async_result = ingest_farm_environment.apply_async(
        kwargs={
            "farm_id": farm_id,
            "start": start.isoformat() if isinstance(start, date) else start,
            "end": end.isoformat() if isinstance(end, date) else end,
            "requested_by_id": requested_by_id,
            "force": force,
            "fetch_job_id": fetch_job_id,
        },
        countdown=countdown,
    )
    logger.info("Queued NASA ingestion for farm %s as task %s", farm_id, async_result.id)
    return async_result.id


def _resolve_range(start: str | date | None, end: str | date | None) -> tuple[date, date]:
    default_start, default_end = default_date_range()
    resolved_start = _coerce_date(start, default_start)
    resolved_end = _coerce_date(end, default_end)
    if resolved_start > resolved_end:
        raise ValueError(
            f"start ({resolved_start.isoformat()}) must not be after end ({resolved_end.isoformat()})."
        )
    return resolved_start, resolved_end


def _coerce_date(value: str | date | None, fallback: date) -> date:
    if value in (None, ""):
        return fallback
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Unparseable date {value!r}; expected YYYY-MM-DD.") from exc


def _requested_by(requested_by_id: int | None):
    if not requested_by_id:
        return None
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(pk=requested_by_id).first()


def _handle_power_failure(task, exc: PowerError, job: DataFetchJob, farm: Farm, query: PowerQuery):
    """Retry transient failures, otherwise close the job and return the summary."""
    max_retries = int(_config("NASA_POWER_TASK_MAX_RETRIES", DEFAULT_MAX_RETRIES))
    retries_done = getattr(task.request, "retries", 0) or 0

    if isinstance(exc, PowerTransientError) and retries_done < max_retries:
        backoff = int(_config("NASA_POWER_TASK_RETRY_BACKOFF_SECONDS", DEFAULT_RETRY_BACKOFF_SECONDS))
        countdown = max(1, backoff * (2**retries_done))
        logger.warning(
            "Transient NASA failure for farm %s (attempt %s/%s), retrying in %ss: %s",
            farm.id,
            retries_done + 1,
            max_retries + 1,
            countdown,
            exc,
        )
        raise task.retry(
            exc=exc,
            countdown=countdown,
            max_retries=max_retries,
            kwargs={
                "farm_id": farm.id,
                "start": query.start.isoformat(),
                "end": query.end.isoformat(),
                "requested_by_id": job.requested_by_id,
                "force": True,
                "fetch_job_id": str(job.pk),
            },
        )

    record_fetch_failure(job, exc)
    logger.error(
        "NASA ingestion failed for farm %s (job %s, %s): %s",
        farm.id,
        job.pk,
        exc.code,
        exc.message,
    )
    return {
        "status": "failed",
        "farm_id": farm.id,
        "job_id": str(job.pk),
        "error_code": exc.code,
        "error_message": exc.message,
        "details": list(exc.details),
        "attempts": retries_done + 1,
        "parameters": list(query.parameters),
    }
