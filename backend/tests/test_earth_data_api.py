"""REST API tests for environmental data (Phase 3E).

NASA HTTP is mocked; the Celery enqueue point is patched so no broker is needed.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.earth_data.models import DataFetchJob, EnvironmentalObservation
from apps.earth_data.services import persist_power_response, record_fetch_failure, start_fetch_job
from apps.earth_data.providers.power import RECOMMENDED_PARAMETERS, PowerQuery
from apps.earth_data.tasks import ingest_farm_environment
from apps.farms.models import Farm
from tests.test_earth_data_persistence import DATES, build_response, make_farm
from tests.test_earth_data_tasks import FakePowerClient, use_client

User = get_user_model()

PASSWORD = "AgroSpace!2026pass"


def daily_url(farm_id: int) -> str:
    return f"/api/v1/farms/{farm_id}/environment/daily/"


def scan_url(farm_id: int) -> str:
    return f"/api/v1/farms/{farm_id}/scans/"


def job_url(job_id) -> str:
    return f"/api/v1/data-jobs/{job_id}/"


class BaseApiTest(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="owner", password=PASSWORD)
        self.other = User.objects.create_user(username="other", password=PASSWORD)
        self.farm = make_farm("API Farm", "owner")
        self.other_farm = make_farm("Other Farm", "other")

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.other_client = APIClient()
        self.other_client.force_authenticate(self.other)

    def seed_observations(self, farm: Farm | None = None, **overrides) -> None:
        farm = farm or self.farm
        response = build_response(overrides or None)
        persist_power_response(start_fetch_job(farm=farm, query=response.query), response)


class AuthenticationTests(BaseApiTest):
    def test_all_endpoints_require_authentication(self) -> None:
        anonymous = APIClient()
        self.assertEqual(anonymous.get(daily_url(self.farm.id)).status_code, 401)
        self.assertEqual(anonymous.post(scan_url(self.farm.id), {}, format="json").status_code, 401)
        self.assertEqual(anonymous.get(job_url("00000000-0000-0000-0000-000000000000")).status_code, 401)

    def test_owner_can_read_own_data(self) -> None:
        self.seed_observations()
        self.assertEqual(self.owner_client.get(daily_url(self.farm.id)).status_code, 200)


class OwnershipTests(BaseApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.seed_observations()
        job = DataFetchJob.objects.filter(farm=self.farm).first()
        self.job_id = job.pk

    def test_other_farmer_cannot_read_observations(self) -> None:
        response = self.other_client.get(daily_url(self.farm.id))
        self.assertEqual(response.status_code, 404)

    def test_other_farmer_cannot_request_a_scan(self) -> None:
        response = self.other_client.post(
            scan_url(self.farm.id),
            {"start": "2024-02-01", "end": "2024-02-03"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(DataFetchJob.objects.filter(farm=self.farm).count(), 1)

    def test_other_farmer_cannot_read_job_status(self) -> None:
        self.assertEqual(self.other_client.get(job_url(self.job_id)).status_code, 404)

    def test_owner_can_read_job_status(self) -> None:
        self.assertEqual(self.owner_client.get(job_url(self.job_id)).status_code, 200)

    def test_unknown_job_is_404(self) -> None:
        response = self.owner_client.get(job_url("11111111-1111-1111-1111-111111111111"))
        self.assertEqual(response.status_code, 404)


class ObservationRetrievalTests(BaseApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.seed_observations()

    def test_successful_retrieval_includes_units_and_provenance(self) -> None:
        response = self.owner_client.get(daily_url(self.farm.id), {"start": "2024-01-01", "end": "2024-01-07"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["farm_id"], self.farm.id)
        self.assertEqual(payload["count"], 49)
        self.assertEqual(payload["range"], {"start": "2024-01-01", "end": "2024-01-07"})

        metadata = {item["code"]: item for item in payload["parameters"]}
        self.assertEqual(metadata["T2M"]["units"], "C")
        self.assertEqual(metadata["PRECTOTCORR"]["units"], "mm/day")
        self.assertEqual(metadata["T2M"]["data_category"], "REANALYSIS_OR_ASSIMILATION_ESTIMATE")

        spatial = payload["spatial"]
        self.assertEqual(spatial["time_standard"], "UTC")
        self.assertEqual(spatial["requested"]["longitude"], "30.950000")
        self.assertEqual(spatial["returned"]["longitude"], "30.951000")
        self.assertIn("grid-cell", spatial["note"])

        first = payload["results"][0]
        self.assertEqual(first["date"], "2024-01-01")
        self.assertEqual(first["parameter"], "ALLSKY_SFC_SW_DWN")
        self.assertEqual(first["unit"], "MJ/m^2/day")
        self.assertEqual(first["source"], "NASA_POWER")
        self.assertEqual(first["quality_status"], "AVAILABLE")
        # No raw provider payload or internal model ids leak.
        self.assertNotIn("id", first)
        self.assertNotIn("properties", payload)

    def test_date_filtering(self) -> None:
        response = self.owner_client.get(
            daily_url(self.farm.id),
            {"start": "2024-01-02", "end": "2024-01-03", "parameter": "T2M"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual([row["date"] for row in payload["results"]], ["2024-01-02", "2024-01-03"])
        self.assertEqual(payload["range"], {"start": "2024-01-02", "end": "2024-01-03"})

    def test_parameter_filtering_accepts_comma_list(self) -> None:
        response = self.owner_client.get(
            daily_url(self.farm.id),
            {"parameter": "T2M,PRECTOTCORR", "start": "2024-01-01", "end": "2024-01-07"},
        )
        payload = response.json()
        self.assertEqual(payload["count"], 14)
        self.assertEqual({row["parameter"] for row in payload["results"]}, {"T2M", "PRECTOTCORR"})

    def test_parameter_filtering_accepts_repeated_values(self) -> None:
        response = self.owner_client.get(
            daily_url(self.farm.id)
            + "?parameter=T2M&parameter=WS2M&start=2024-01-01&end=2024-01-07"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["parameter"] for row in response.json()["results"]}, {"T2M", "WS2M"})

    def test_pagination(self) -> None:
        first = self.owner_client.get(daily_url(self.farm.id), {"start": "2024-01-01", "end": "2024-01-07"}).json()
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(first["count"], 49)
        self.assertIsNotNone(first["next"])
        self.assertIsNone(first["previous"])

        third = self.owner_client.get(daily_url(self.farm.id), {"page": 3, "start": "2024-01-01", "end": "2024-01-07"}).json()
        self.assertEqual(len(third["results"]), 9)  # 49 - 20 - 20
        self.assertIsNone(third["next"])
        self.assertIsNotNone(third["previous"])

    def test_missing_values_are_null_with_missing_status(self) -> None:
        missing = build_response({"T2M": {"20240102": -999.0}})
        farm = make_farm("Missing Farm", "missing_owner")
        client = APIClient()
        client.force_authenticate(User.objects.get(username="missing_owner"))
        persist_power_response(start_fetch_job(farm=farm, query=missing.query), missing)

        payload = client.get(
            daily_url(farm.id), {"parameter": "T2M", "start": "2024-01-02", "end": "2024-01-02"}
        ).json()
        row = payload["results"][0]
        self.assertIsNone(row["value"])
        self.assertEqual(row["quality_status"], "MISSING")

    def test_solar_units_and_metadata_are_reported(self) -> None:
        payload = self.owner_client.get(
            daily_url(self.farm.id),
            {"parameter": "ALLSKY_SFC_SW_DWN", "start": "2024-01-01", "end": "2024-01-07"},
        ).json()
        metadata = payload["parameters"][0]
        self.assertEqual(metadata["code"], "ALLSKY_SFC_SW_DWN")
        self.assertEqual(metadata["units"], "MJ/m^2/day")
        self.assertEqual(metadata["product"], "CERES SYN1deg")
        self.assertEqual(metadata["first_available_date"], "1984-01-01")


class ObservationValidationTests(BaseApiTest):
    def test_invalid_date_format(self) -> None:
        response = self.owner_client.get(daily_url(self.farm.id), {"start": "not-a-date"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("start", response.json())

    def test_start_after_end(self) -> None:
        response = self.owner_client.get(
            daily_url(self.farm.id), {"start": "2024-01-07", "end": "2024-01-01"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("start", response.json())

    def test_range_above_limit_is_rejected(self) -> None:
        response = self.owner_client.get(
            daily_url(self.farm.id), {"start": "2023-01-01", "end": "2025-01-01"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end", response.json())

    def test_unknown_parameter_is_rejected(self) -> None:
        response = self.owner_client.get(daily_url(self.farm.id), {"parameter": "NOPE"})
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("parameter", body)
        self.assertIn("T2M", " ".join(body["parameter"]))

    def test_future_end_is_rejected(self) -> None:
        future = (date.today() + timedelta(days=1)).isoformat()
        response = self.owner_client.get(
            daily_url(self.farm.id), {"start": date.today().isoformat(), "end": future}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("end", response.json())

    def test_solar_before_1984_is_rejected(self) -> None:
        response = self.owner_client.get(
            daily_url(self.farm.id),
            {"start": "1981-01-01", "end": "1981-06-30", "parameter": "ALLSKY_SFC_SW_DWN"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("1984-01-01", " ".join(response.json()["start"]))

    def test_default_window_is_bounded(self) -> None:
        payload = self.owner_client.get(daily_url(self.farm.id)).json()
        start = date.fromisoformat(payload["range"]["start"])
        end = date.fromisoformat(payload["range"]["end"])
        self.assertLessEqual((end - start).days + 1, 366)


class ScanRequestTests(BaseApiTest):
    def _enqueue(self, task_id: str = "task-abc") -> mock.Mock:
        return mock.Mock(return_value=task_id)

    def test_successful_refresh_returns_202_with_identifiers(self) -> None:
        enqueue = self._enqueue()
        with mock.patch("apps.earth_data.views.enqueue_farm_fetch", enqueue):
            response = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07"},
                format="json",
            )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "QUEUED")
        self.assertEqual(body["farm_id"], self.farm.id)
        self.assertEqual(body["task_id"], "task-abc")
        self.assertEqual(body["start"], "2024-01-01")
        self.assertEqual(body["end"], "2024-01-07")
        self.assertEqual(body["parameters"], list(RECOMMENDED_PARAMETERS))
        self.assertEqual(body["status_url"], f"/api/v1/data-jobs/{body['job_id']}/")

        job = DataFetchJob.objects.get(pk=body["job_id"])
        self.assertEqual(job.status, DataFetchJob.Status.RUNNING)
        self.assertEqual(job.farm, self.farm)
        self.assertEqual(job.requested_by, self.owner)

        enqueue.assert_called_once()
        kwargs = enqueue.call_args.kwargs
        self.assertEqual(kwargs["fetch_job_id"], str(job.pk))
        self.assertEqual(kwargs["farm"], self.farm)

    def test_duplicate_refresh_is_rejected_with_409(self) -> None:
        query = PowerQuery(latitude=30.79, longitude=30.95, start=DATES[0], end=DATES[-1])
        running = start_fetch_job(farm=self.farm, query=query)
        enqueue = self._enqueue()

        with mock.patch("apps.earth_data.views.enqueue_farm_fetch", enqueue):
            response = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07", "force": True},
                format="json",
            )

        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["status"], "already_running")
        self.assertEqual(body["job_id"], str(running.pk))
        enqueue.assert_not_called()
        self.assertEqual(DataFetchJob.objects.filter(farm=self.farm).count(), 1)

    def test_already_current_range_is_not_enqueued(self) -> None:
        self.seed_observations()
        enqueue = self._enqueue()
        with mock.patch("apps.earth_data.views.enqueue_farm_fetch", enqueue):
            response = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "already_current")
        enqueue.assert_not_called()

    def test_force_refreshes_even_when_data_exists(self) -> None:
        self.seed_observations()
        enqueue = self._enqueue()
        with mock.patch("apps.earth_data.views.enqueue_farm_fetch", enqueue):
            response = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07", "force": True},
                format="json",
            )

        self.assertEqual(response.status_code, 202)
        enqueue.assert_called_once()

    def test_invalid_dates_and_parameters_are_rejected(self) -> None:
        cases = [
            ({"start": "2024-01-07", "end": "2024-01-01"}, "start"),
            ({"start": "bad-date"}, "start"),
            ({"parameters": ["NOPE"]}, "parameter"),
            ({"start": "1981-01-01", "end": "1981-06-30", "parameters": ["ALLSKY_SFC_SW_DWN"]}, "start"),
        ]
        for body, field in cases:
            with self.subTest(body=body):
                response = self.owner_client.post(scan_url(self.farm.id), body, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertEqual(DataFetchJob.objects.count(), 0)

    def test_parameter_count_limit_is_enforced(self) -> None:
        too_many = [f"P{i}" for i in range(21)]
        response = self.owner_client.post(
            scan_url(self.farm.id), {"parameters": too_many}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("At most 20", " ".join(response.json()["parameter"]))
        self.assertEqual(DataFetchJob.objects.count(), 0)

    def test_enqueue_failure_marks_the_job_failed_and_returns_503(self) -> None:
        with mock.patch(
            "apps.earth_data.views.enqueue_farm_fetch", side_effect=RuntimeError("broker down")
        ):
            response = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07"},
                format="json",
            )

        self.assertEqual(response.status_code, 503)
        body = response.json()
        job = DataFetchJob.objects.get(pk=body["job_id"])
        self.assertEqual(job.status, DataFetchJob.Status.FAILED)
        self.assertIn("broker", job.error_message)

    def test_point_only_farm_can_be_scanned(self) -> None:
        # make_farm() creates a location-only farm (no boundary).
        self.assertIsNone(self.farm.boundary)
        enqueue = self._enqueue()
        with mock.patch("apps.earth_data.views.enqueue_farm_fetch", enqueue):
            response = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07"},
                format="json",
            )

        self.assertEqual(response.status_code, 202)
        job = DataFetchJob.objects.get(pk=response.json()["job_id"])
        self.assertEqual(job.request_geometry_source, "FARMER_LOCATION")


class JobStatusTests(BaseApiTest):
    def test_job_status_exposes_progress_and_failure_fields(self) -> None:
        query = PowerQuery(latitude=30.79, longitude=30.95, start=DATES[0], end=DATES[-1])
        job = start_fetch_job(farm=self.farm, query=query, requested_by=self.owner)
        record_fetch_failure(job, RuntimeError("provider exploded with secret token abc123"))

        response = self.owner_client.get(job_url(job.pk))
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["job_id"], str(job.pk))
        self.assertEqual(body["farm_id"], self.farm.id)
        self.assertEqual(body["status"], "FAILED")
        self.assertEqual(body["error_code"], "unknown_error")
        self.assertEqual(body["parameters"], list(RECOMMENDED_PARAMETERS))
        self.assertEqual(body["days_requested"], 7)
        self.assertEqual(body["status_url"], f"/api/v1/data-jobs/{job.pk}/")
        self.assertIsNotNone(body["finished_at"])
        self.assertNotIn("traceback", response.content.decode().lower())

    def test_successful_job_reports_counts(self) -> None:
        self.seed_observations()
        job = DataFetchJob.objects.get(farm=self.farm)
        body = self.owner_client.get(job_url(job.pk)).json()
        self.assertEqual(body["status"], "SUCCEEDED")
        self.assertEqual(body["days_stored"], 7)
        self.assertEqual(body["days_missing"], 0)


class EndToEndApiTests(BaseApiTest):
    """API → Celery task → persistence → retrieval, with NASA mocked."""

    def test_scan_then_read_observations(self) -> None:
        response_fixture = build_response()

        def inline_enqueue(**kwargs):
            with use_client(FakePowerClient(response=response_fixture)):
                result = ingest_farm_environment(
                    farm_id=kwargs["farm"].id,
                    start=kwargs["start"],
                    end=kwargs["end"],
                    requested_by_id=getattr(kwargs.get("requested_by"), "pk", None),
                    fetch_job_id=kwargs["fetch_job_id"],
                    force=True,
                )
            self.assertEqual(result["status"], "SUCCEEDED")
            return "inline-task"

        with mock.patch("apps.earth_data.views.enqueue_farm_fetch", side_effect=inline_enqueue):
            scan = self.owner_client.post(
                scan_url(self.farm.id),
                {"start": "2024-01-01", "end": "2024-01-07"},
                format="json",
            )

        self.assertEqual(scan.status_code, 202)
        job_id = scan.json()["job_id"]

        status_response = self.owner_client.get(job_url(job_id)).json()
        self.assertEqual(status_response["status"], "SUCCEEDED")
        self.assertEqual(status_response["days_stored"], 7)

        observations = self.owner_client.get(
            daily_url(self.farm.id), {"start": "2024-01-01", "end": "2024-01-07"}
        ).json()
        self.assertEqual(observations["count"], 49)
        t2m = next(row for row in observations["results"] if row["parameter"] == "T2M")
        self.assertEqual(Decimal(t2m["value"]), Decimal("16.1500"))
        self.assertEqual(EnvironmentalObservation.objects.filter(farm=self.farm).count(), 49)
