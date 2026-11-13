"""Environmental summary API tests (Phase 4D) — deterministic fixtures, no network."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.earth_data.models import DatasetSource, EnvironmentalObservation
from apps.earth_data.services import persist_power_response, start_fetch_job
from apps.farms.models import FarmerContext
from tests.test_earth_data_persistence import DATES, build_response, make_farm

User = get_user_model()
PASSWORD = "AgroSpace!2026pass"


def summary_url(farm_id: int) -> str:
    return f"/api/v1/farms/{farm_id}/environment/summary/".replace(
        "/environment/summary/", "/environment/current/"
    )


class SummaryApiBase(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="summary_owner", password=PASSWORD)
        self.other = User.objects.create_user(username="summary_other", password=PASSWORD)
        self.farm = make_farm("Summary Farm", "summary_owner")

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.other_client = APIClient()
        self.other_client.force_authenticate(self.other)

    def seed_observations(self, farm=None, **overrides) -> None:
        farm = farm or self.farm
        response = build_response(overrides or None)
        persist_power_response(start_fetch_job(farm=farm, query=response.query), response)

    def seed_full_context(self, farm=None) -> FarmerContext:
        return FarmerContext.objects.create(
            farm=farm or self.farm,
            soil_source="LAB_TEST",
            texture_class="clay_loam",
            ph=Decimal("7.80"),
            organic_carbon_percent=Decimal("1.20"),
            nitrogen_ppm=Decimal("22.50"),
            phosphorus_ppm=Decimal("11.00"),
            potassium_ppm=Decimal("180.00"),
            sampling_depth_cm=30,
            sampling_method="composite",
            lab_name="Delta Soil Lab",
            sample_date=date(2026, 3, 15),
            irrigation_available=True,
            irrigation_type="surface_canal",
            water_reliability="seasonal_variable",
        )


class SummaryPermissionTests(SummaryApiBase):
    def test_anonymous_is_rejected(self) -> None:
        self.assertEqual(APIClient().get(summary_url(self.farm.id)).status_code, 401)

    def test_other_farmer_gets_404(self) -> None:
        self.seed_observations()
        self.assertEqual(self.other_client.get(summary_url(self.farm.id)).status_code, 404)

    def test_nonexistent_farm_gets_404(self) -> None:
        self.assertEqual(self.owner_client.get(summary_url(999_999)).status_code, 404)

    def test_owner_gets_200_even_without_data(self) -> None:
        response = self.owner_client.get(summary_url(self.farm.id))
        self.assertEqual(response.status_code, 200)


class SummaryWindowTests(SummaryApiBase):
    def setUp(self) -> None:
        super().setUp()
        self.seed_observations()

    def test_default_window_is_30_days_ending_at_latest_observation(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        window = payload["window"]

        self.assertEqual(window["days"], 30)
        self.assertEqual(window["end"], DATES[-1].isoformat())
        self.assertEqual(window["start"], (DATES[-1] - timedelta(days=29)).isoformat())
        self.assertEqual(window["latest_observation"], DATES[-1].isoformat())

    def test_custom_window(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id), {"window_days": 7}).json()
        self.assertEqual(payload["window"]["days"], 7)
        self.assertEqual(payload["window"]["start"], DATES[0].isoformat())
        self.assertEqual(payload["window"]["end"], DATES[-1].isoformat())

    def test_minimum_window_of_one_day(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id), {"window_days": 1}).json()
        self.assertEqual(payload["window"]["days"], 1)
        self.assertEqual(payload["window"]["start"], DATES[-1].isoformat())
        self.assertEqual(payload["window"]["end"], DATES[-1].isoformat())

    def test_maximum_window_of_366_days(self) -> None:
        response = self.owner_client.get(summary_url(self.farm.id), {"window_days": 366})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["window"]["days"], 366)

    def test_invalid_windows_are_rejected(self) -> None:
        for value in (0, -5, 367, 1000, "abc", "1.5"):
            with self.subTest(value=value):
                response = self.owner_client.get(summary_url(self.farm.id), {"window_days": value})
                self.assertEqual(response.status_code, 400)
                self.assertIn("window_days", response.json())


class SummaryStructureTests(SummaryApiBase):
    def setUp(self) -> None:
        super().setUp()
        self.seed_observations()
        self.seed_full_context()

    def test_all_four_indicators_are_present(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(set(payload["indicators"]), {"water", "heat", "soil", "market"})
        for code, indicator in payload["indicators"].items():
            self.assertEqual(indicator["code"], code.upper())
            self.assertIn("status", indicator)
            self.assertIn("confidence", indicator)
            self.assertIn("as_of", indicator)
            self.assertIn("period", indicator)
            self.assertIn("measurements", indicator)
            self.assertIn("missing", indicator)
            self.assertIn("methodology", indicator)
            self.assertIn("sources", indicator)
            self.assertIn("limitations", indicator)

    def test_market_is_always_unavailable(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        market = payload["indicators"]["market"]
        self.assertEqual(market["status"], "UNAVAILABLE")
        self.assertEqual(market["confidence"], "NONE")
        self.assertEqual(market["measurements"], [])
        self.assertIsNone(market["as_of"])
        self.assertIsNone(market["period"])

    def test_no_numeric_scores(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        for indicator in payload["indicators"].values():
            self.assertIsNone(indicator["score"])

    def test_top_level_fields(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["farm_id"], self.farm.id)
        self.assertIn("generated_at", payload)
        self.assertIn("data_status", payload)
        self.assertIn("freshness", payload)
        self.assertIn("limitations", payload)
        self.assertEqual(payload["freshness"]["latest_observation"], DATES[-1].isoformat())

    def test_as_of_per_indicator(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["indicators"]["water"]["as_of"], DATES[-1].isoformat())
        self.assertEqual(payload["indicators"]["heat"]["as_of"], DATES[-1].isoformat())
        self.assertEqual(payload["indicators"]["soil"]["as_of"], "2026-03-15")
        self.assertIsNone(payload["indicators"]["market"]["as_of"])

    def test_soil_is_not_given_the_climate_window(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id), {"window_days": 7}).json()
        soil = payload["indicators"]["soil"]
        self.assertEqual(soil["period"]["start"], "2026-03-15")
        self.assertEqual(soil["period"]["end"], "2026-03-15")

    def test_irrigation_context_is_reported(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        context = {item["name"]: item for item in payload["indicators"]["water"]["context"]}
        self.assertEqual(context["irrigation_available"]["value"], "yes")
        self.assertEqual(context["irrigation_type"]["value"], "surface_canal")
        self.assertEqual(context["irrigation_available"]["quality"], "FARMER_REPORTED")

    def test_no_real_time_claims(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["window"]["end"], payload["window"]["latest_observation"])
        self.assertTrue(any("not real-time" in text for text in payload["limitations"]))
        self.assertTrue(any("grid-cell" in text for text in payload["limitations"]))


class SummaryDataStatusTests(SummaryApiBase):
    def test_no_observations_and_no_context_is_insufficient(self) -> None:
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["data_status"], "INSUFFICIENT_DATA")
        self.assertEqual(payload["indicators"]["water"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(payload["indicators"]["heat"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(payload["indicators"]["soil"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(payload["indicators"]["market"]["status"], "UNAVAILABLE")
        self.assertIsNone(payload["window"]["latest_observation"])
        self.assertEqual(payload["freshness"]["status"], "UNKNOWN")

    def test_no_observations_but_soil_context_is_partial(self) -> None:
        self.seed_full_context()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["data_status"], "PARTIAL")
        self.assertEqual(payload["indicators"]["soil"]["status"], "OK")
        self.assertEqual(payload["indicators"]["water"]["status"], "INSUFFICIENT_DATA")

    def test_sparse_history_is_partial_with_coverage(self) -> None:
        self.seed_observations()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        water = payload["indicators"]["water"]

        self.assertEqual(payload["data_status"], "PARTIAL")
        self.assertEqual(water["status"], "PARTIAL")
        self.assertEqual(water["coverage"]["days_expected"], 30)
        self.assertEqual(water["coverage"]["days_covered"], 7)
        self.assertEqual(water["coverage"]["days_missing"], 23)

    def test_complete_window_and_soil_is_ok(self) -> None:
        self.seed_observations()
        self.seed_full_context()
        payload = self.owner_client.get(summary_url(self.farm.id), {"window_days": 7}).json()
        self.assertEqual(payload["indicators"]["water"]["status"], "OK")
        self.assertEqual(payload["indicators"]["heat"]["status"], "OK")
        self.assertEqual(payload["indicators"]["soil"]["status"], "OK")
        self.assertEqual(payload["data_status"], "OK")

    def test_missing_soil_profile_is_insufficient(self) -> None:
        self.seed_observations()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["indicators"]["soil"]["status"], "INSUFFICIENT_DATA")
        self.assertEqual(payload["data_status"], "PARTIAL")

    def test_partial_soil_profile_is_partial(self) -> None:
        self.seed_observations()
        FarmerContext.objects.create(
            farm=self.farm, soil_source="FARMER_REPORTED", ph=Decimal("7.10")
        )
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        soil = payload["indicators"]["soil"]
        self.assertEqual(soil["status"], "PARTIAL")
        self.assertEqual(soil["completeness"]["properties_present"], 1)


class SummaryFreshnessTests(SummaryApiBase):
    def test_stale_observations_are_obvious(self) -> None:
        self.seed_observations()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()

        expected_age = (date.today() - DATES[-1]).days
        self.assertEqual(payload["window"]["age_days"], expected_age)
        self.assertEqual(payload["freshness"]["age_days"], expected_age)
        self.assertEqual(payload["freshness"]["status"], "STALE")
        self.assertEqual(payload["window"]["freshness"], "STALE")

    def test_latest_observation_date_is_reported(self) -> None:
        self.seed_observations()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        self.assertEqual(payload["window"]["latest_observation"], DATES[-1].isoformat())
        self.assertEqual(payload["indicators"]["heat"]["period"]["latest_observation"], DATES[-1].isoformat())


class SummaryPerformanceTests(SummaryApiBase):
    def test_summary_uses_a_bounded_number_of_queries(self) -> None:
        self.seed_observations()
        self.seed_full_context()
        with self.assertNumQueries(6):
            response = self.owner_client.get(summary_url(self.farm.id))
        self.assertEqual(response.status_code, 200)


class Phase4FRegressionTests(SummaryApiBase):
    """Regression coverage for the issues identified during the Phase 4F review."""

    def _source(self, parameter_code: str) -> DatasetSource:
        return DatasetSource.objects.get(
            provider="NASA_POWER", parameter_code=parameter_code, is_active=True
        )

    def test_missing_quality_row_does_not_advance_the_window(self) -> None:
        """A stored MISSING row is not an observation and must not extend the window."""
        self.seed_observations()
        later = DATES[-1] + timedelta(days=3)
        EnvironmentalObservation.objects.create(
            farm=self.farm,
            source=self._source("PRECTOTCORR"),
            observation_date=later,
            value=None,
            quality_status=EnvironmentalObservation.QualityStatus.MISSING,
            requested_longitude=Decimal("30.95"),
            requested_latitude=Decimal("30.79"),
        )

        payload = self.owner_client.get(summary_url(self.farm.id)).json()

        self.assertEqual(payload["window"]["end"], DATES[-1].isoformat())
        self.assertEqual(payload["window"]["latest_observation"], DATES[-1].isoformat())
        self.assertEqual(payload["freshness"]["latest_observation"], DATES[-1].isoformat())
        self.assertEqual(
            payload["indicators"]["water"]["as_of"], DATES[-1].isoformat()
        )

    def test_top_level_freshness_follows_usable_catalogue_observations(self) -> None:
        """Top-level freshness is documented as the newest usable observation for any active
        parameter; indicator periods still reflect only the inputs that indicator used."""
        self.seed_observations()
        newer = DATES[-1] + timedelta(days=2)
        EnvironmentalObservation.objects.create(
            farm=self.farm,
            source=self._source("RH2M"),
            observation_date=newer,
            value=Decimal("55.0000"),
            quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
            requested_longitude=Decimal("30.95"),
            requested_latitude=Decimal("30.79"),
        )

        payload = self.owner_client.get(summary_url(self.farm.id)).json()

        self.assertEqual(payload["window"]["end"], newer.isoformat())
        self.assertEqual(payload["freshness"]["latest_observation"], newer.isoformat())
        # The indicator evidence did not change with the non-indicator parameter.
        self.assertEqual(payload["indicators"]["water"]["as_of"], DATES[-1].isoformat())
        self.assertEqual(payload["indicators"]["heat"]["as_of"], DATES[-1].isoformat())

    def test_soil_without_sample_date_has_no_synthetic_period(self) -> None:
        FarmerContext.objects.create(
            farm=self.farm,
            soil_source="FARMER_REPORTED",
            texture_class="clay_loam",
            ph=Decimal("7.40"),
            sample_date=None,
        )

        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        soil = payload["indicators"]["soil"]

        self.assertEqual(soil["status"], "PARTIAL")
        self.assertIsNone(soil["period"])
        self.assertIsNone(soil["as_of"])
        self.assertIn("sample_date", {item["name"] for item in soil["missing"]})
        self.assertNotEqual(soil["as_of"], date.today().isoformat())

    def test_soil_sample_date_is_used_verbatim(self) -> None:
        self.seed_full_context()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        soil = payload["indicators"]["soil"]

        self.assertEqual(soil["period"]["start"], "2026-03-15")
        self.assertEqual(soil["period"]["end"], "2026-03-15")
        self.assertEqual(soil["as_of"], "2026-03-15")
        self.assertNotEqual(soil["as_of"], date.today().isoformat())

    def test_market_unavailable_with_null_score_and_period(self) -> None:
        self.seed_full_context()
        payload = self.owner_client.get(summary_url(self.farm.id)).json()
        market = payload["indicators"]["market"]

        self.assertEqual(market["status"], "UNAVAILABLE")
        self.assertIsNone(market["score"])
        self.assertIsNone(market["period"])
        self.assertIsNone(market["as_of"])
        self.assertEqual(market["measurements"], [])

    def test_a_missing_water_series_does_not_invalidate_heat_or_soil(self) -> None:
        FarmerContext.objects.create(
            farm=self.farm,
            soil_source="LAB_TEST",
            texture_class="clay_loam",
            ph=Decimal("7.80"),
            organic_carbon_percent=Decimal("1.20"),
            nitrogen_ppm=Decimal("22.50"),
            phosphorus_ppm=Decimal("11.00"),
            potassium_ppm=Decimal("180.00"),
            sampling_method="composite",
            sample_date=date(2026, 3, 15),
        )
        response = build_response({"PRECTOTCORR": {d.strftime("%Y%m%d"): None for d in DATES}})
        persist_power_response(start_fetch_job(farm=self.farm, query=response.query), response)

        payload = self.owner_client.get(summary_url(self.farm.id), {"window_days": 7}).json()

        self.assertEqual(payload["indicators"]["water"]["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(payload["indicators"]["water"]["measurements"][0]["value"])
        self.assertEqual(payload["indicators"]["heat"]["status"], "OK")
        self.assertEqual(payload["indicators"]["soil"]["status"], "OK")
        self.assertEqual(payload["data_status"], "PARTIAL")
