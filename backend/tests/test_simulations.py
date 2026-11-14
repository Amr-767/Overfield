"""Phase 6 scenario simulation: pure determinism, honesty and owner scoping."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.simulations.models import SimulationRun, SimulationStep
from apps.simulations.service import (
    ENGINE_VERSION,
    ScenarioValidationError,
    build_simulation,
    resolve_scenario,
)
from tests.test_earth_data_persistence import DATES, build_response, make_farm

from apps.earth_data.services import persist_power_response, start_fetch_job


User = get_user_model()


def seed_observations(farm, overrides=None) -> None:
    response = build_response(overrides)
    job = start_fetch_job(farm=farm, query=response.query)
    persist_power_response(job, response)


class SimulationServiceTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm("Simulation farm", "simulation-farmer")
        seed_observations(self.farm)

    def simulate(self, mode: str, **kwargs):
        scenario = resolve_scenario(mode, **kwargs)
        return build_simulation(self.farm, scenario=scenario, window_days=7)

    def test_baseline_identity_matches_stored_evidence(self) -> None:
        payload = self.simulate("BASELINE")

        self.assertEqual(payload["status"], "COMPLETED")
        self.assertEqual(payload["baseline"]["period"]["start"], "2024-01-01")
        self.assertEqual(payload["baseline"]["period"]["end"], "2024-01-07")
        self.assertEqual(payload["baseline"]["period"]["latest_observation"], "2024-01-07")
        self.assertEqual(payload["baseline"]["metrics"]["mean_temperature_c"], "15.90")
        self.assertEqual(payload["baseline"]["metrics"]["rainfall_total_mm"], "0.51")
        self.assertEqual(payload["baseline"]["metrics"]["rainy_days"], 0)
        self.assertEqual(payload["differences"], {})
        self.assertEqual(len(payload["steps"]), 4)
        for step in payload["steps"]:
            self.assertEqual(step["metrics"], payload["baseline"]["metrics"])

    def test_hot_scenario_changes_only_the_explainable_temperature_evidence(self) -> None:
        farm = make_farm("Hot scenario farm", "hot-scenario-farmer")
        seed_observations(
            farm,
            {"T2M_MAX": {day.strftime("%Y%m%d"): 34.0 for day in DATES}},
        )
        baseline = build_simulation(farm, scenario=resolve_scenario("BASELINE"), window_days=7)
        hot = build_simulation(farm, scenario=resolve_scenario("HOT_SCENARIO"), window_days=7)

        self.assertEqual(baseline["baseline"]["metrics"]["hot_days_max_temperature_ge_35c"], 0)
        self.assertEqual(hot["steps"][0]["metrics"]["hot_days_max_temperature_ge_35c"], 7)
        # +2.00 °C on every stored maximum: 34 -> 36.
        self.assertEqual(hot["steps"][0]["metrics"]["mean_max_temperature_c"], "36.00")
        self.assertEqual(hot["differences"]["mean_max_temperature_c"]["change"], "2.00")
        self.assertEqual(hot["differences"]["hot_days_max_temperature_ge_35c"]["change"], 7)
        # Rainfall is untouched by a temperature-only scenario.
        self.assertEqual(
            hot["steps"][0]["metrics"]["rainfall_total_mm"],
            baseline["baseline"]["metrics"]["rainfall_total_mm"],
        )

    def test_dry_scenario_reduces_rainfall_explainably(self) -> None:
        dry = self.simulate("DRY_SCENARIO")

        self.assertEqual(dry["steps"][0]["metrics"]["rainfall_total_mm"], "0.36")
        self.assertEqual(dry["differences"]["rainfall_total_mm"]["baseline"], "0.51")
        self.assertEqual(dry["differences"]["rainfall_total_mm"]["change"], "-0.15")
        # Temperature is untouched by a rainfall-only scenario.
        self.assertEqual(dry["steps"][0]["metrics"]["mean_temperature_c"], "15.90")

    def test_missing_values_stay_missing_after_adjustment(self) -> None:
        farm = make_farm("Missing rainfall farm", "missing-rain-farmer")
        seed_observations(farm, {"PRECTOTCORR": {"20240107": -999}})

        payload = build_simulation(
            farm, scenario=resolve_scenario("CUSTOM", rainfall_multiplier="0.50"), window_days=7
        )

        self.assertEqual(payload["steps"][0]["metrics"]["days_with_rainfall"], 6)
        self.assertEqual(payload["steps"][0]["metrics"]["rainfall_total_mm"], "0.04")
        self.assertIn(
            "Rainfall total covers 6 of 7 days; missing days are not imputed.",
            payload["limitations"],
        )

    def test_bounds_and_ambiguous_scenarios_are_rejected(self) -> None:
        with self.assertRaises(ScenarioValidationError):
            resolve_scenario("CUSTOM", temperature_delta_c="6")
        with self.assertRaises(ScenarioValidationError):
            resolve_scenario("CUSTOM", rainfall_multiplier="0.1")
        with self.assertRaises(ScenarioValidationError):
            resolve_scenario("CUSTOM")
        with self.assertRaises(ScenarioValidationError):
            resolve_scenario("BASELINE", temperature_delta_c="1")
        with self.assertRaises(ScenarioValidationError):
            resolve_scenario("HOT_SCENARIO", temperature_delta_c="3")
        with self.assertRaises(ScenarioValidationError):
            resolve_scenario("NOT_A_MODE")

    def test_reproducibility_is_byte_identical(self) -> None:
        scenario = resolve_scenario("CUSTOM", temperature_delta_c="1.5", rainfall_multiplier="0.8")
        first = build_simulation(self.farm, scenario=scenario, window_days=7)
        second = build_simulation(self.farm, scenario=scenario, window_days=7)

        self.assertEqual(first["input_sha256"], second["input_sha256"])
        self.assertEqual(len(first["input_sha256"]), 64)
        self.assertEqual(first, second)
        self.assertEqual(first["engine_version"], ENGINE_VERSION)

    def test_no_observations_yields_explicit_insufficient_evidence(self) -> None:
        farm = make_farm("Empty simulation farm", "empty-sim-farmer")
        payload = build_simulation(farm, scenario=resolve_scenario("HOT_SCENARIO"), window_days=7)

        self.assertEqual(payload["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(payload["baseline"]["metrics"])
        self.assertEqual(payload["differences"], {})
        self.assertEqual(len(payload["steps"]), 4)
        for step in payload["steps"]:
            self.assertEqual(step["status"], "INSUFFICIENT_EVIDENCE")
            self.assertIn(
                "NASA POWER environmental observations for this farm", step["missing_inputs"]
            )
            self.assertIsNone(step["metrics"]["mean_temperature_c"])
            self.assertIsNone(step["metrics"]["rainfall_total_mm"])
            self.assertEqual(step["metrics"]["days_with_rainfall"], 0)

    def test_output_has_no_score_ranking_or_crop_claim(self) -> None:
        payload = self.simulate("CUSTOM", temperature_delta_c="2", rainfall_multiplier="0.7")

        self.assertIsNone(payload["comparison"]["score"])
        self.assertFalse(payload["comparison"]["ranked"])
        self.assertEqual(payload["crop_level_outcomes"], "NOT_SIMULATED")
        self.assertIn("not a NASA forecast", payload["hypothetical_notice"])
        self.assertIn(
            "No approved regional crop calendar exists, so crop-level scenario outcomes are not simulated.",
            payload["limitations"],
        )

    def test_horizon_checkpoints_never_assert_a_future_date(self) -> None:
        payload = self.simulate("BASELINE")

        self.assertEqual(
            [step["horizon_months"] for step in payload["steps"]], [0, 6, 12, 24]
        )
        for step in payload["steps"]:
            self.assertIsNone(step["as_of_date"])
        for step in payload["steps"]:
            if step["horizon_months"]:
                self.assertIn(
                    "not a future observation or a forecast", " ".join(step["assumptions"])
                )


class SimulationApiTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm("API simulation farm", "simulation-api-owner")
        self.owner = self.farm.owner
        self.other = User.objects.create_user(username="simulation-api-other", password="pass")
        seed_observations(self.farm)
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.other_client = APIClient()
        self.other_client.force_authenticate(self.other)
        self.url = f"/api/v1/farms/{self.farm.pk}/simulations/"

    def test_anonymous_is_denied(self) -> None:
        anonymous = APIClient()
        self.assertEqual(anonymous.post(self.url, {}, format="json").status_code, 401)
        self.assertEqual(anonymous.get(self.url).status_code, 401)

    def test_other_farmer_cannot_read_or_write(self) -> None:
        self.assertEqual(self.other_client.post(self.url, {}, format="json").status_code, 404)

        created = self.owner_client.post(self.url, {"window_days": 7}, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        simulation_id = created.data["simulation_id"]

        self.assertEqual(
            self.other_client.get(f"/api/v1/simulations/{simulation_id}/").status_code, 404
        )
        self.assertEqual(
            self.other_client.get(f"/api/v1/simulations/{simulation_id}/steps/").status_code,
            404,
        )

    def test_create_persists_run_and_steps_with_a_reproducible_hash(self) -> None:
        response = self.owner_client.post(
            self.url, {"scenario_mode": "CUSTOM", "temperature_delta_c": "2", "window_days": 7},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "COMPLETED")
        self.assertEqual(response.data["scenario"]["mode"], "CUSTOM")
        self.assertEqual(len(response.data["steps"]), 4)
        self.assertEqual(len(response.data["input_sha256"]), 64)

        run = SimulationRun.objects.get(pk=response.data["simulation_id"])
        self.assertEqual(run.input_sha256, response.data["input_sha256"])
        self.assertEqual(run.farm, self.farm)
        self.assertEqual(run.requested_by, self.owner)
        self.assertEqual(SimulationStep.objects.filter(run=run).count(), 4)

        detail = self.owner_client.get(f"/api/v1/simulations/{run.pk}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["input_sha256"], run.input_sha256)

        steps = self.owner_client.get(f"/api/v1/simulations/{run.pk}/steps/")
        self.assertEqual(steps.status_code, status.HTTP_200_OK)
        self.assertEqual(len(steps.data["steps"]), 4)
        self.assertEqual(steps.data["crop_level_outcomes"], "NOT_SIMULATED")

    def test_repeat_request_same_inputs_same_hash(self) -> None:
        first = self.owner_client.post(self.url, {"scenario_mode": "HOT_SCENARIO"}, format="json")
        second = self.owner_client.post(self.url, {"scenario_mode": "HOT_SCENARIO"}, format="json")

        self.assertEqual(first.data["input_sha256"], second.data["input_sha256"])
        self.assertNotEqual(first.data["simulation_id"], second.data["simulation_id"])

    def test_invalid_scenario_requests_are_rejected(self) -> None:
        cases = [
            {"scenario_mode": "CUSTOM"},
            {"scenario_mode": "CUSTOM", "temperature_delta_c": "9"},
            {"scenario_mode": "BASELINE", "temperature_delta_c": "1"},
            {"scenario_mode": "UNKNOWN"},
            {"window_days": 400},
        ]
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(
                    self.owner_client.post(self.url, body, format="json").status_code, 400
                )

    def test_crop_level_requests_are_refused_honestly(self) -> None:
        response = self.owner_client.post(self.url, {"planning_seasons": 4}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("planning_seasons", response.data)
        self.assertIn("approved regional crop catalogue", str(response.data["planning_seasons"]))

    def test_empty_farm_returns_insufficient_evidence_not_a_fake_value(self) -> None:
        farm = make_farm("Empty API farm", "empty-api-farmer")
        client = APIClient()
        client.force_authenticate(farm.owner)

        response = client.post(
            f"/api/v1/farms/{farm.pk}/simulations/", {"window_days": 7}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(response.data["baseline"]["metrics"])
        self.assertTrue(
            all(step["status"] == "INSUFFICIENT_EVIDENCE" for step in response.data["steps"])
        )

    def test_list_returns_only_this_farms_runs(self) -> None:
        self.owner_client.post(self.url, {"window_days": 7}, format="json")

        response = self.owner_client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["farm_id"], self.farm.pk)
