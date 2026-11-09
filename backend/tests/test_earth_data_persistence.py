"""Persistence tests for environmental data (Phase 3C). No network involved."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.earth_data.exceptions import PowerTransientError
from apps.earth_data.models import (
    DataFetchJob,
    DatasetSource,
    EnvironmentalObservation,
)
from apps.earth_data.providers.power import (
    RECOMMENDED_PARAMETERS,
    PowerQuery,
    parse_daily_response,
)
from apps.earth_data.services import (
    SourceCatalogueError,
    get_farm_observations,
    get_farm_series,
    persist_power_response,
    record_fetch_failure,
    start_fetch_job,
)
from apps.farms.models import Farm

User = get_user_model()

DATES = [date(2024, 1, day) for day in range(1, 8)]
VALUES: dict[str, list[float]] = {
    "T2M": [16.15, 16.43, 15.90, 15.12, 15.60, 16.68, 15.42],
    "T2M_MAX": [22.23, 22.68, 21.82, 22.11, 22.84, 23.60, 24.58],
    "T2M_MIN": [11.05, 11.20, 10.80, 9.90, 10.20, 11.40, 10.10],
    "PRECTOTCORR": [0.0, 0.0, 0.0, 0.0, 0.08, 0.01, 0.42],
    "RH2M": [62.0, 60.5, 58.0, 55.2, 61.4, 63.0, 59.9],
    "WS2M": [2.1, 2.4, 1.9, 2.6, 3.1, 2.2, 1.8],
    "ALLSKY_SFC_SW_DWN": [12.24, 12.60, 11.90, 12.05, 12.80, 13.10, 12.45],
}


def build_payload(overrides: dict[str, dict[str, float | None]] | None = None) -> dict:
    overrides = overrides or {}
    series = {}
    for code in RECOMMENDED_PARAMETERS:
        day_values = {
            day.strftime("%Y%m%d"): value for day, value in zip(DATES, VALUES[code], strict=True)
        }
        day_values.update(overrides.get(code, {}))
        series[code] = day_values
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [30.951, 30.791, 4.96]},
        "header": {
            "title": "NASA/POWER Source Native Resolution Daily Data",
            "api": {"version": "v2.10.3", "name": "POWER Daily API"},
            "sources": ["MERRA2", "SYN1DEG", "POWER"],
            "fill_value": -999.0,
            "time_standard": "UTC",
        },
        "messages": [],
        "parameters": {
            code: {"units": _units(code), "longname": code} for code in RECOMMENDED_PARAMETERS
        },
        "properties": {"parameter": series},
        "times": {"data": 0.1, "process": 0.01},
    }


def _units(code: str) -> str:
    return {
        "T2M": "C",
        "T2M_MAX": "C",
        "T2M_MIN": "C",
        "PRECTOTCORR": "mm/day",
        "RH2M": "%",
        "WS2M": "m/s",
        "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
    }[code]


def build_response(overrides: dict[str, dict[str, float | None]] | None = None):
    query = PowerQuery(
        latitude=30.79,
        longitude=30.95,
        start=DATES[0],
        end=DATES[-1],
        parameters=RECOMMENDED_PARAMETERS,
    )
    return parse_daily_response(json.dumps(build_payload(overrides)), query)


def make_farm(name: str = "Persistence Farm", username: str = "farmer") -> Farm:
    user, _ = User.objects.get_or_create(username=username)
    return Farm.objects.create(
        owner=user,
        name=name,
        country_code="EG",
        region_code="Gharbia",
        timezone="Africa/Cairo",
        location=Point(30.95, 30.79, srid=4326),
        area_hectares=Decimal("3.7882"),
        area_source=Farm.AreaSource.FARMER_REPORTED,
        geometry_source=Farm.GeometrySource.LOCATION_POINT,
    )


class CatalogueTests(TestCase):
    def test_seed_migration_created_the_verified_catalogue(self) -> None:
        sources = DatasetSource.objects.all()
        self.assertEqual(sources.count(), 7)
        self.assertEqual(
            set(sources.values_list("parameter_code", flat=True)), set(RECOMMENDED_PARAMETERS)
        )

        t2m = DatasetSource.objects.get(parameter_code="T2M")
        self.assertEqual(t2m.units, "C")
        self.assertEqual(t2m.product, "MERRA-2")
        self.assertEqual(t2m.daily_aggregation, "MEAN")
        self.assertEqual(t2m.data_category, "REANALYSIS_OR_ASSIMILATION_ESTIMATE")
        self.assertEqual(t2m.first_available_date, date(1981, 1, 1))
        self.assertTrue(t2m.is_active)

        solar = DatasetSource.objects.get(parameter_code="ALLSKY_SFC_SW_DWN")
        self.assertEqual(solar.units, "MJ/m^2/day")
        self.assertEqual(solar.first_available_date, date(1984, 1, 1))
        self.assertEqual(solar.native_resolution_note, "")  # unverified, not invented

        precip = DatasetSource.objects.get(parameter_code="PRECTOTCORR")
        self.assertEqual(precip.daily_aggregation, "TOTAL")


class FetchJobTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm()
        self.user = self.farm.owner
        self.response = build_response()

    def test_start_fetch_job_records_the_request(self) -> None:
        job = start_fetch_job(
            farm=self.farm, query=self.response.query, requested_by=self.user
        )

        self.assertEqual(job.status, DataFetchJob.Status.RUNNING)
        self.assertEqual(job.farm, self.farm)
        self.assertEqual(job.requested_by, self.user)
        self.assertEqual(job.parameters, list(RECOMMENDED_PARAMETERS))
        self.assertEqual(job.requested_start, DATES[0])
        self.assertEqual(job.requested_end, DATES[-1])
        self.assertEqual(job.days_requested, 7)
        self.assertIsNotNone(job.started_at)
        self.assertEqual(job.requested_latitude, Decimal("30.790000"))
        self.assertEqual(job.requested_longitude, Decimal("30.950000"))

    def test_persist_creates_observations_and_closes_the_job(self) -> None:
        job = start_fetch_job(farm=self.farm, query=self.response.query)
        result = persist_power_response(job, self.response)

        self.assertEqual(result.created_rows, 49)  # 7 parameters x 7 days
        self.assertEqual(result.updated_rows, 0)
        self.assertEqual(result.missing_values, 0)
        self.assertEqual(result.days_stored, 7)
        self.assertEqual(result.days_missing, 0)
        self.assertEqual(result.status, DataFetchJob.Status.SUCCEEDED)

        job.refresh_from_db()
        self.assertEqual(job.status, DataFetchJob.Status.SUCCEEDED)
        self.assertEqual(job.days_stored, 7)
        self.assertEqual(job.days_missing, 0)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNotNone(job.duration_ms)

    def test_observations_preserve_decimal_precision(self) -> None:
        job = start_fetch_job(farm=self.farm, query=self.response.query)
        persist_power_response(job, self.response)

        observation = EnvironmentalObservation.objects.get(
            farm=self.farm, source__parameter_code="T2M", observation_date=DATES[0]
        )
        self.assertEqual(observation.value, Decimal("16.1500"))
        self.assertIsInstance(observation.value, Decimal)
        self.assertEqual(observation.requested_longitude, Decimal("30.950000"))
        self.assertEqual(observation.returned_longitude, Decimal("30.951000"))


class IdempotencyTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm()

    def test_repeat_import_does_not_duplicate_observations(self) -> None:
        first_response = build_response()
        first_job = start_fetch_job(farm=self.farm, query=first_response.query)
        persist_power_response(first_job, first_response)
        self.assertEqual(EnvironmentalObservation.objects.count(), 49)

        second_response = build_response({"T2M": {DATES[0].strftime("%Y%m%d"): 17.99}})
        second_job = start_fetch_job(farm=self.farm, query=second_response.query)
        result = persist_power_response(second_job, second_response)

        self.assertEqual(EnvironmentalObservation.objects.count(), 49)
        self.assertEqual(result.created_rows, 0)
        self.assertEqual(result.updated_rows, 49)

        refreshed = EnvironmentalObservation.objects.get(
            farm=self.farm, source__parameter_code="T2M", observation_date=DATES[0]
        )
        self.assertEqual(refreshed.value, Decimal("17.9900"))
        self.assertEqual(refreshed.fetch_job_id, second_job.id)

    def test_database_unique_constraint_blocks_manual_duplicates(self) -> None:
        job = start_fetch_job(farm=self.farm, query=build_response().query)
        persist_power_response(job, build_response())
        existing = EnvironmentalObservation.objects.first()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EnvironmentalObservation.objects.create(
                    farm=existing.farm,
                    source=existing.source,
                    observation_date=existing.observation_date,
                    value=Decimal("1.0"),
                    quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
                    requested_longitude=Decimal("30.95"),
                    requested_latitude=Decimal("30.79"),
                )


class MissingValueTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm()

    def test_fill_value_is_stored_as_missing_not_a_number(self) -> None:
        response = build_response({"T2M": {"20240102": -999.0}})
        job = start_fetch_job(farm=self.farm, query=response.query)
        result = persist_power_response(job, response)

        observation = EnvironmentalObservation.objects.get(
            farm=self.farm, source__parameter_code="T2M", observation_date=DATES[1]
        )
        self.assertIsNone(observation.value)
        self.assertEqual(observation.quality_status, EnvironmentalObservation.QualityStatus.MISSING)

        self.assertEqual(result.missing_values, 1)
        self.assertEqual(result.days_missing, 1)
        self.assertEqual(result.status, DataFetchJob.Status.PARTIALLY_SUCCEEDED)

        job.refresh_from_db()
        self.assertEqual(job.status, DataFetchJob.Status.PARTIALLY_SUCCEEDED)
        self.assertEqual(job.days_missing, 1)
        self.assertEqual(job.days_stored, 7)

    def test_quality_and_value_must_agree(self) -> None:
        source = DatasetSource.objects.get(parameter_code="T2M")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EnvironmentalObservation.objects.create(
                    farm=self.farm,
                    source=source,
                    observation_date=DATES[0],
                    value=None,
                    quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
                    requested_longitude=Decimal("30.95"),
                    requested_latitude=Decimal("30.79"),
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EnvironmentalObservation.objects.create(
                    farm=self.farm,
                    source=source,
                    observation_date=DATES[1],
                    value=Decimal("5.0"),
                    quality_status=EnvironmentalObservation.QualityStatus.MISSING,
                    requested_longitude=Decimal("30.95"),
                    requested_latitude=Decimal("30.79"),
                )


class ProvenanceTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm()

    def test_every_observation_is_traceable(self) -> None:
        response = build_response()
        job = start_fetch_job(farm=self.farm, query=response.query)
        persist_power_response(job, response)

        observation = EnvironmentalObservation.objects.select_related("source", "fetch_job").get(
            farm=self.farm, source__parameter_code="PRECTOTCORR", observation_date=DATES[6]
        )

        self.assertEqual(observation.source.provider, "NASA_POWER")
        self.assertEqual(observation.source.parameter_code, "PRECTOTCORR")
        self.assertEqual(observation.source.units, "mm/day")
        self.assertEqual(observation.source.product, "MERRA-2")
        self.assertEqual(observation.source.data_category, "REANALYSIS_OR_ASSIMILATION_ESTIMATE")
        self.assertEqual(observation.observation_date, DATES[6])
        self.assertEqual(observation.farm_id, self.farm.id)
        self.assertEqual(observation.fetch_job_id, job.id)

        # Requested (what we asked for) and returned (POWER's answer) differ.
        job.refresh_from_db()
        self.assertEqual(observation.requested_longitude, Decimal("30.950000"))
        self.assertEqual(observation.returned_longitude, Decimal("30.951000"))
        self.assertEqual(job.returned_elevation_m, Decimal("4.96"))
        self.assertEqual(job.api_version, "v2.10.3")
        self.assertEqual(job.api_name, "POWER Daily API")
        self.assertEqual(job.source_products, ["MERRA2", "SYN1DEG", "POWER"])
        self.assertEqual(job.time_standard, "UTC")

    def test_non_power_payload_is_rejected(self) -> None:
        job = start_fetch_job(farm=self.farm, query=build_response().query)
        with self.assertRaises(TypeError):
            persist_power_response(job, {"T2M": {"20240101": 99.9}})  # type: ignore[arg-type]
        self.assertEqual(EnvironmentalObservation.objects.count(), 0)


class FarmIsolationTests(TestCase):
    def test_two_farms_keep_separate_series(self) -> None:
        farm_a = make_farm("Farm A", "farmer_a")
        farm_b = make_farm("Farm B", "farmer_b")

        response_a = build_response()
        response_b = build_response({"T2M": {"20240101": 40.0}})

        persist_power_response(start_fetch_job(farm=farm_a, query=response_a.query), response_a)
        persist_power_response(start_fetch_job(farm=farm_b, query=response_b.query), response_b)

        self.assertEqual(EnvironmentalObservation.objects.filter(farm=farm_a).count(), 49)
        self.assertEqual(EnvironmentalObservation.objects.filter(farm=farm_b).count(), 49)
        # Same source and date can exist for both farms (uniqueness is per farm).
        self.assertEqual(
            EnvironmentalObservation.objects.filter(
                source__parameter_code="T2M", observation_date=DATES[0]
            ).count(),
            2,
        )

        series_a = get_farm_series(farm_a, "T2M")
        self.assertEqual([row.value for row in series_a][0], Decimal("16.1500"))
        self.assertNotIn(farm_b.id, {row.farm_id for row in series_a})


class DeletionBehaviourTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm()
        job = start_fetch_job(farm=self.farm, query=build_response().query)
        persist_power_response(job, build_response())
        self.job = job

    def test_deleting_the_farm_removes_its_observations_and_jobs(self) -> None:
        self.farm.delete()
        self.assertEqual(EnvironmentalObservation.objects.count(), 0)
        self.assertEqual(DataFetchJob.objects.count(), 0)

    def test_deleting_a_job_keeps_observations_without_the_link(self) -> None:
        self.job.delete()
        self.assertEqual(EnvironmentalObservation.objects.count(), 49)
        self.assertIsNone(EnvironmentalObservation.objects.first().fetch_job_id)

    def test_catalogue_rows_are_protected_while_observations_exist(self) -> None:
        source = DatasetSource.objects.get(parameter_code="T2M")
        with self.assertRaises(ProtectedError):
            source.delete()


class FailureRecordingTests(TestCase):
    def test_failed_fetch_is_recorded_with_provider_details(self) -> None:
        farm = make_farm()
        job = start_fetch_job(farm=farm, query=build_response().query)
        error = PowerTransientError(
            "NASA POWER kept failing with HTTP 503 after 3 attempts.",
            details=("upstream unavailable",),
        )

        record_fetch_failure(job, error)

        job.refresh_from_db()
        self.assertEqual(job.status, DataFetchJob.Status.FAILED)
        self.assertEqual(job.error_code, "power_transient_error")
        self.assertIn("HTTP 503", job.error_message)
        self.assertIn("upstream unavailable", job.error_message)
        self.assertIsNotNone(job.finished_at)
        self.assertIsNotNone(job.duration_ms)
        self.assertEqual(EnvironmentalObservation.objects.count(), 0)


class QueryHelperTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm()
        response = build_response()
        persist_power_response(start_fetch_job(farm=self.farm, query=response.query), response)

    def test_parameter_and_date_filters(self) -> None:
        series = get_farm_series(self.farm, "T2M", start=DATES[2], end=DATES[4])
        self.assertEqual([row.observation_date for row in series], DATES[2:5])
        self.assertTrue(all(row.source.parameter_code == "T2M" for row in series))

    def test_filter_by_multiple_parameters(self) -> None:
        rows = get_farm_observations(self.farm, codes=["T2M", "PRECTOTCORR"], start=DATES[0], end=DATES[0])
        self.assertEqual(rows.count(), 2)
        self.assertEqual(
            {row.source.parameter_code for row in rows}, {"T2M", "PRECTOTCORR"}
        )

    def test_series_is_ordered_by_date(self) -> None:
        dates = [row.observation_date for row in get_farm_series(self.farm, "PRECTOTCORR")]
        self.assertEqual(dates, sorted(dates))


class SourceAvailabilityTests(TestCase):
    def test_inactive_source_is_rejected_before_writing(self) -> None:
        farm = make_farm()
        response = build_response()
        job = start_fetch_job(farm=farm, query=response.query)
        DatasetSource.objects.filter(parameter_code="WS2M").update(is_active=False)

        with self.assertRaises(SourceCatalogueError) as ctx:
            persist_power_response(job, response)

        self.assertIn("WS2M", str(ctx.exception))
        self.assertEqual(EnvironmentalObservation.objects.count(), 0)
