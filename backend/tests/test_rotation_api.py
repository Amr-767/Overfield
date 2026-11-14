"""Rotation API persistence, ownership, and deterministic snapshot tests."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.agronomy.models import RotationRecommendation
from tests.test_earth_data_persistence import make_farm


User = get_user_model()


class RotationApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="rotation-owner", password="secure-pass")
        self.other = User.objects.create_user(username="rotation-other", password="secure-pass")
        self.farm = make_farm("Rotation farm", "rotation-owner")
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.other_client = APIClient()
        self.other_client.force_authenticate(self.other)
        self.url = f"/api/v1/farms/{self.farm.pk}/recommendations/"

    def test_anonymous_cannot_generate_or_read_recommendation(self):
        self.assertEqual(APIClient().post(self.url, {}, format="json").status_code, 401)

    def test_other_farmer_cannot_generate_for_farm_or_read_result(self):
        self.assertEqual(self.other_client.post(self.url, {}, format="json").status_code, 404)
        result = self.owner_client.post(self.url, {}, format="json")
        self.assertEqual(result.status_code, 201)
        detail = f"/api/v1/recommendations/{result.data['recommendation_id']}/"
        self.assertEqual(self.other_client.get(detail).status_code, 404)

    def test_empty_catalog_is_stored_as_reproducible_insufficient_evidence(self):
        response = self.owner_client.post(self.url, {"planning_seasons": 4}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(response.data["options"], [])
        self.assertTrue(response.data["input_sha256"])
        row = RotationRecommendation.objects.get(pk=response.data["recommendation_id"])
        self.assertEqual(row.input_sha256, response.data["input_sha256"])
        self.assertEqual(row.input_snapshot["planning_seasons"], 4)

    def test_retrieve_explanation_and_compare_are_owner_scoped(self):
        first = self.owner_client.post(self.url, {"planning_seasons": 3}, format="json")
        second = self.owner_client.post(self.url, {"planning_seasons": 3}, format="json")
        rec_id = first.data["recommendation_id"]
        detail = f"/api/v1/recommendations/{rec_id}/"
        self.assertEqual(self.owner_client.get(detail).status_code, 200)
        explanation = self.owner_client.get(detail + "explanation/")
        self.assertEqual(explanation.status_code, 200)
        self.assertIn("missing", explanation.data)
        comparison = self.owner_client.get(detail + "compare/", {"with": second.data["recommendation_id"]})
        self.assertEqual(comparison.status_code, 200)
        self.assertTrue(comparison.data["same_input"])
        self.assertEqual(self.other_client.get(detail + "explanation/").status_code, 404)

    def test_invalid_horizon_and_priorities_rejected(self):
        for payload in ({"planning_seasons": 0}, {"planning_seasons": 13}, {"priority_weights": {"water_conservation": 0.4}}):
            with self.subTest(payload=payload):
                self.assertEqual(self.owner_client.post(self.url, payload, format="json").status_code, 400)

    def test_requested_region_must_match_farm_region(self):
        response = self.owner_client.post(self.url, {"region_code": "OTHER-REGION"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "INSUFFICIENT_EVIDENCE")
        self.assertIn("region_code_mismatch", {item["name"] for item in response.data["missing"]})
