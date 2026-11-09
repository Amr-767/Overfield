"""Celery ingestion task tests (Phase 3D) — mocked NASA, no broker required."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.test import TestCase
from django.utils import timezone

from apps.earth_data.exceptions import PowerRequestError, PowerTransientError
from apps.earth_data.ingestion import default_date_range, resolve_farm_point
from apps.earth_data.models import DataFetchJob, DatasetSource, EnvironmentalObservation
from apps.earth_data.providers.power import RECOMMENDED_PARAMETERS, PowerQuery
from apps.earth_data.services import start_fetch_job
from apps.earth_data.tasks import (
    TASK_NAME,
    enqueue_farm_fetch,
    ingest_farm_environment,
)
from apps.farms.models import Farm
from tests.test_earth_data_persistence import DATES, build_response, make_farm

User = get_user_model()


class FakePowerClient:
    def __init__(self, *, response=None, error: BaseException | None = None, errors=None) -> None:
        self.response = response
        self.error = error
        self.errors = list(errors or [])
        self.calls: list[PowerQuery] = []

    def fetch(self, query: PowerQuery):
        self.calls.append(query)
        if self.errors:
            raise self.errors.pop(0)
        if self.error is not None:
            raise self.error
        return self.response


class _RetrySignal(Exception):
    """Raised by the patched ``retry`` to stop the task body in tests."""


@contextmanager
def with_retries(count: int):
    ingest_farm_environment.push_request(retries=count)
    try:
        yield
    finally:
        ingest_farm_environment.pop_request()


def use_client(client: FakePowerClient):
    return mock.patch("apps.earth_data.tasks.get_power_client", return_value=client)


class SuccessfulTaskTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm("Task Farm", "task_farmer")
        self.response = build_response()

    def test_successful_task_persists_and_reports_counts(self) -> None:
        client = FakePowerClient(response=self.response)
        with use_client(client):
            result = ingest_farm_environment(
                farm_id=self.farm.id,
                start=DATES[0].isoformat(),
                end=DATES[-1].isoformat(),
            )

        self.assertEqual(result["status"], DataFetchJob.Status.SUCCEEDED)
        self.assertEqual(result["created_rows"], 49)
        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(result["missing_values"], 0)
        self.assertEqual(result["days_stored"], 7)
        self.assertEqual(result["farm_id"], self.farm.id)
        self.assertEqual(len(client.calls), 1)

        job = DataFetchJob.objects.get(pk=result["job_id"])
        self.assertEqual(job.status, DataFetchJob.Status.SUCCEEDED)
        self.assertEqual(job.farm, self.farm)
        self.assertEqual(job.days_requested, 7)
        self.assertEqual(job.requested_start, DATES[0])
        self.assertEqual(job.requested_end, DATES[-1])
        self.assertEqual(job.parameters, list(RECOMMENDED_PARAMETERS))
        self.assertEqual(job.request_geometry_source, "FARMER_LOCATION")
        self.assertIsNotNone(job.finished_at)
        self.assertEqual(EnvironmentalObservation.objects.filter(farm=self.farm).count(), 49)

    def test_partial_success_when_days_are_missing(self) -> None:
        response = build_response({"T2M": {"20240103": -999.0}})
        with use_client(FakePowerClient(response=response)):
            result = ingest_farm_environment(
                farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
            )

        self.assertEqual(result["status"], DataFetchJob.Status.PARTIALLY_SUCCEEDED)
        self.assertEqual(result["missing_values"], 1)
        self.assertEqual(result["days_missing"], 1)
        missing = EnvironmentalObservation.objects.get(
            farm=self.farm, source__parameter_code="T2M", observation_date=date(2024, 1, 3)
        )
        self.assertIsNone(missing.value)
        self.assertEqual(missing.quality_status, "MISSING")

    def test_repeat_run_skips_when_data_is_current(self) -> None:
        with use_client(FakePowerClient(response=self.response)):
            ingest_farm_environment(
                farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
            )

        client = FakePowerClient(response=self.response)
        with use_client(client):
            result = ingest_farm_environment(
                farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
            )

        self.assertEqual(result["status"], "already_current")
        self.assertEqual(client.calls, [])  # no unnecessary provider request
        self.assertEqual(DataFetchJob.objects.count(), 1)
        self.assertEqual(EnvironmentalObservation.objects.count(), 49)

    def test_force_refresh_updates_existing_rows(self) -> None:
        with use_client(FakePowerClient(response=self.response)):
            ingest_farm_environment(
                farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
            )
        original_job = DataFetchJob.objects.get()

        changed = build_response({"T2M": {"20240101": 21.50}})
        with use_client(FakePowerClient(response=changed)):
            result = ingest_farm_environment(
                farm_id=self.farm.id,
                start=DATES[0].isoformat(),
                end=DATES[-1].isoformat(),
                force=True,
            )

        self.assertEqual(result["created_rows"], 0)
        self.assertEqual(result["updated_rows"], 49)
        self.assertEqual(EnvironmentalObservation.objects.count(), 49)
        refreshed = EnvironmentalObservation.objects.get(
            farm=self.farm, source__parameter_code="T2M", observation_date=DATES[0]
        )
        self.assertEqual(refreshed.value, Decimal("21.5000"))
        self.assertNotEqual(str(refreshed.fetch_job_id), str(original_job.pk))


class FailureTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm("Failure Farm", "failure_farmer")

    def test_permanent_failure_is_recorded_without_retry(self) -> None:
        error = PowerRequestError(
            "NASA POWER rejected the request with HTTP 422.",
            details=("One of your parameters is incorrect: BOGUSPARAM.",),
        )

        with use_client(FakePowerClient(error=error)) as _:
            with mock.patch.object(ingest_farm_environment, "retry") as retry_mock:
                result = ingest_farm_environment(
                    farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
                )

        retry_mock.assert_not_called()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "power_request_error")
        self.assertIn("422", result["error_message"])
        self.assertIn("BOGUSPARAM", " ".join(result["details"]))

        job = DataFetchJob.objects.get(pk=result["job_id"])
        self.assertEqual(job.status, DataFetchJob.Status.FAILED)
        self.assertEqual(job.error_code, "power_request_error")
        self.assertIn("BOGUSPARAM", job.error_message)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNotNone(job.duration_ms)
        self.assertEqual(EnvironmentalObservation.objects.count(), 0)

    def test_transient_failure_schedules_a_bounded_retry(self) -> None:
        error = PowerTransientError("NASA POWER kept failing with HTTP 503 after 3 attempts.")

        with use_client(FakePowerClient(error=error)):
            with mock.patch.object(ingest_farm_environment, "retry", side_effect=_RetrySignal) as retry_mock:
                with self.assertRaises(_RetrySignal):
                    ingest_farm_environment(
                        farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
                    )

        retry_mock.assert_called_once()
        kwargs = retry_mock.call_args.kwargs
        self.assertEqual(kwargs["countdown"], 5)  # base backoff for attempt 1
        self.assertEqual(kwargs["max_retries"], 2)
        self.assertEqual(kwargs["kwargs"]["farm_id"], self.farm.id)
        self.assertIn("fetch_job_id", kwargs["kwargs"])

        # The job stays RUNNING so the retry can continue it; nothing was written.
        job = DataFetchJob.objects.get()
        self.assertEqual(job.status, DataFetchJob.Status.RUNNING)
        self.assertEqual(EnvironmentalObservation.objects.count(), 0)
        self.assertEqual(str(job.pk), kwargs["kwargs"]["fetch_job_id"])

    def test_retry_continues_the_same_job_and_succeeds(self) -> None:
        error = PowerTransientError("HTTP 503")
        with use_client(FakePowerClient(error=error)):
            with mock.patch.object(ingest_farm_environment, "retry", side_effect=_RetrySignal) as retry_mock:
                with self.assertRaises(_RetrySignal):
                    ingest_farm_environment(
                        farm_id=self.farm.id,
                        start=DATES[0].isoformat(),
                        end=DATES[-1].isoformat(),
                    )

        retry_kwargs = retry_mock.call_args.kwargs["kwargs"]
        with use_client(FakePowerClient(response=build_response())):
            result = ingest_farm_environment(
                farm_id=retry_kwargs["farm_id"],
                start=retry_kwargs["start"],
                end=retry_kwargs["end"],
                fetch_job_id=retry_kwargs["fetch_job_id"],
                force=retry_kwargs["force"],
            )

        self.assertEqual(result["status"], DataFetchJob.Status.SUCCEEDED)
        self.assertEqual(DataFetchJob.objects.count(), 1)  # no duplicate job row
        self.assertEqual(result["job_id"], retry_kwargs["fetch_job_id"])
        self.assertEqual(EnvironmentalObservation.objects.count(), 49)

    def test_exhausted_retries_mark_the_job_failed(self) -> None:
        error = PowerTransientError("NASA POWER request failed after 3 attempts.")
        with use_client(FakePowerClient(error=error)):
            with with_retries(settings.NASA_POWER_TASK_MAX_RETRIES):
                result = ingest_farm_environment.run(
                    farm_id=self.farm.id,
                    start=DATES[0].isoformat(),
                    end=DATES[-1].isoformat(),
                )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "power_transient_error")
        self.assertEqual(result["attempts"], settings.NASA_POWER_TASK_MAX_RETRIES + 1)
        job = DataFetchJob.objects.get()
        self.assertEqual(job.status, DataFetchJob.Status.FAILED)

    def test_failed_request_does_not_corrupt_existing_observations(self) -> None:
        with use_client(FakePowerClient(response=build_response())):
            ingest_farm_environment(
                farm_id=self.farm.id, start=DATES[0].isoformat(), end=DATES[-1].isoformat()
            )
        before = list(
            EnvironmentalObservation.objects.filter(farm=self.farm)
            .order_by("id")
            .values_list("id", "value", "quality_status")
        )

        error = PowerTransientError("provider unavailable")
        with use_client(FakePowerClient(error=error)):
            with with_retries(settings.NASA_POWER_TASK_MAX_RETRIES):
                result = ingest_farm_environment.run(
                    farm_id=self.farm.id,
                    start=DATES[0].isoformat(),
                    end=DATES[-1].isoformat(),
                    force=True,
                )

        self.assertEqual(result["status"], "failed")
        after = list(
            EnvironmentalObservation.objects.filter(farm=self.farm)
            .order_by("id")
            .values_list("id", "value", "quality_status")
        )
        self.assertEqual(before, after)  # IDs, values and quality untouched
        self.assertEqual(
            DataFetchJob.objects.filter(status=DataFetchJob.Status.SUCCEEDED).count(), 1
        )
        self.assertEqual(DataFetchJob.objects.filter(status=DataFetchJob.Status.FAILED).count(), 1)


class GuardTests(TestCase):
    def test_missing_farm_returns_a_clear_result_and_creates_nothing(self) -> None:
        client = FakePowerClient(response=build_response())
        with use_client(client):
            result = ingest_farm_environment(farm_id=999_999)

        self.assertEqual(result["status"], "farm_not_found")
        self.assertEqual(DataFetchJob.objects.count(), 0)
        self.assertEqual(client.calls, [])

    def test_invalid_range_is_rejected_before_any_request(self) -> None:
        farm = make_farm("Range Farm", "range_farmer")
        client = FakePowerClient(response=build_response())
        with use_client(client):
            result = ingest_farm_environment(
                farm_id=farm.id, start="2024-01-07", end="2024-01-01"
            )

        self.assertEqual(result["status"], "invalid_range")
        self.assertEqual(DataFetchJob.objects.count(), 0)
        self.assertEqual(client.calls, [])

    def test_duplicate_concurrent_scan_is_rejected(self) -> None:
        farm = make_farm("Busy Farm", "busy_farmer")
        query = PowerQuery(
            latitude=30.79, longitude=30.95, start=DATES[0], end=DATES[-1]
        )
        running = start_fetch_job(farm=farm, query=query)

        client = FakePowerClient(response=build_response())
        with use_client(client):
            result = ingest_farm_environment(
                farm_id=farm.id,
                start=DATES[0].isoformat(),
                end=DATES[-1].isoformat(),
                force=True,
            )

        self.assertEqual(result["status"], "already_running")
        self.assertEqual(result["job_id"], str(running.pk))
        self.assertEqual(client.calls, [])  # provider not called twice
        self.assertEqual(DataFetchJob.objects.count(), 1)

    def test_stale_running_job_is_retired_and_replaced(self) -> None:
        farm = make_farm("Stale Farm", "stale_farmer")
        query = PowerQuery(latitude=30.79, longitude=30.95, start=DATES[0], end=DATES[-1])
        stale = start_fetch_job(farm=farm, query=query)
        DataFetchJob.objects.filter(pk=stale.pk).update(
            started_at=timezone.now() - timedelta(seconds=settings.NASA_FETCH_STALE_JOB_SECONDS + 60)
        )

        with use_client(FakePowerClient(response=build_response())):
            result = ingest_farm_environment(
                farm_id=farm.id,
                start=DATES[0].isoformat(),
                end=DATES[-1].isoformat(),
                force=True,
            )

        stale.refresh_from_db()
        self.assertEqual(stale.status, DataFetchJob.Status.FAILED)
        self.assertEqual(stale.error_code, "stale_job")
        self.assertEqual(result["status"], DataFetchJob.Status.SUCCEEDED)
        self.assertNotEqual(result["job_id"], str(stale.pk))
        self.assertEqual(DataFetchJob.objects.count(), 2)

    def test_empty_range_uses_the_bounded_default_window(self) -> None:
        farm = make_farm("Default Farm", "default_farmer")
        with use_client(FakePowerClient(response=build_response())):
            result = ingest_farm_environment(farm_id=farm.id)

        expected_start, expected_end = default_date_range()
        job = DataFetchJob.objects.get(pk=result["job_id"])
        self.assertEqual(job.requested_start, expected_start)
        self.assertEqual(job.requested_end, expected_end)
        self.assertLess((expected_end - expected_start).days, 366)


class CoordinateStrategyTests(TestCase):
    def test_boundary_farm_uses_point_on_surface_of_the_largest_part(self) -> None:
        owner = User.objects.create_user(username="geo_farmer")
        small = Polygon(
            ((30.90, 30.70), (30.91, 30.70), (30.91, 30.71), (30.90, 30.71), (30.90, 30.70)),
            srid=4326,
        )
        large = Polygon(
            ((31.00, 30.80), (31.02, 30.80), (31.02, 30.82), (31.00, 30.82), (31.00, 30.80)),
            srid=4326,
        )
        farm = Farm.objects.create(
            owner=owner,
            name="Two Blocks",
            location=Point(30.9, 30.7, srid=4326),
            boundary=MultiPolygon(small, large, srid=4326),
            area_hectares=Decimal("500.0"),
        )

        point = resolve_farm_point(farm)

        self.assertEqual(point.geometry_source, "POINT_ON_SURFACE")
        self.assertTrue(farm.boundary.contains(Point(point.longitude, point.latitude, srid=4326)))
        # The representative point belongs to the larger part.
        self.assertGreaterEqual(point.longitude, 31.00)
        self.assertGreaterEqual(point.latitude, 30.80)

    def test_location_only_farm_keeps_the_farmer_point(self) -> None:
        farm = make_farm("Point Farm", "point_farmer")  # location=Point(30.95, 30.79)
        point = resolve_farm_point(farm)
        self.assertEqual(point.geometry_source, "FARMER_LOCATION")
        self.assertAlmostEqual(point.longitude, 30.95, places=6)
        self.assertAlmostEqual(point.latitude, 30.79, places=6)


class EnqueueTests(TestCase):
    def test_enqueue_returns_a_task_id_without_running_anything(self) -> None:
        farm = make_farm("Queue Farm", "queue_farmer")
        fake = mock.Mock()
        fake.id = "task-123"

        with mock.patch.object(ingest_farm_environment, "apply_async", return_value=fake) as apply_mock:
            task_id = enqueue_farm_fetch(
                farm=farm, start=date(2024, 1, 1), end=date(2024, 1, 7), force=True
            )

        self.assertEqual(task_id, "task-123")
        kwargs = apply_mock.call_args.kwargs["kwargs"]
        self.assertEqual(kwargs["farm_id"], farm.id)
        self.assertEqual(kwargs["start"], "2024-01-01")
        self.assertEqual(kwargs["end"], "2024-01-07")
        self.assertTrue(kwargs["force"])
        self.assertEqual(DataFetchJob.objects.count(), 0)  # nothing happened yet

    def test_task_metadata_is_registered(self) -> None:
        self.assertEqual(ingest_farm_environment.name, TASK_NAME)
        self.assertEqual(ingest_farm_environment.rate_limit, "12/m")
        self.assertGreater(ingest_farm_environment.soft_time_limit, 0)
        self.assertGreater(ingest_farm_environment.time_limit, 0)
        # No recurring schedule was introduced.
        self.assertEqual(getattr(settings, "CELERY_BEAT_SCHEDULE", {}), {})
