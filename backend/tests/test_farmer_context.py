"""Farmer context: soil, water, crops, priorities, constraints and provenance."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.farms.models import FarmerContext

User = get_user_model()

POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [30.9501, 30.7901],
            [30.9522, 30.7901],
            [30.9522, 30.7918],
            [30.9501, 30.7918],
            [30.9501, 30.7901],
        ]
    ],
}


class FarmerContextTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="farmer1", password="AgroSpace!2026pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        created = self.client.post(
            "/api/v1/farms/", {"name": "North Field", "boundary": POLYGON}, format="json"
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.farm_id = created.data["id"]
        self.url = f"/api/v1/farms/{self.farm_id}/context/"

    def test_context_is_created_empty_and_unknown(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["farm_id"], self.farm_id)
        self.assertIsNone(response.data["ph"])
        self.assertIsNone(response.data["irrigation_available"])
        self.assertEqual(response.data["priorities"], {})
        self.assertEqual(response.data["constraints"], {})
        self.assertEqual(response.data["current_crops"], [])
        self.assertTrue(FarmerContext.objects.filter(farm_id=self.farm_id).exists())

    def test_patch_saves_soil_water_crops_priorities_constraints(self) -> None:
        payload = {
            "soil_source": "LAB_TEST",
            "texture_class": "clay_loam",
            "ph": "7.80",
            "organic_carbon_percent": "1.20",
            "nitrogen_ppm": "22.50",
            "phosphorus_ppm": "11.00",
            "potassium_ppm": "180.00",
            "sampling_depth_cm": 30,
            "lab_name": "Delta Soil Lab",
            "sampling_method": "composite",
            "sample_date": "2026-03-15",
            "water_source": "FARMER_REPORTED",
            "irrigation_available": True,
            "irrigation_type": "surface_canal",
            "water_reliability": "seasonal_variable",
            "priorities": {
                "water_conservation": 0.4,
                "soil_regeneration": 0.3,
                "market_income": 0.2,
                "forage_value": 0.1,
            },
            "constraints": {
                "equipment": ["no_mechanized_harvester"],
                "seed_availability": "unknown",
                "labor_availability": "family_labor_only",
            },
            "current_crops": [
                {"season": "Winter 2025/26", "crop": "Wheat"},
                {"season": "Summer 2026", "crop": "Maize"},
            ],
        }
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["soil_source"], "LAB_TEST")
        self.assertEqual(response.data["texture_class"], "clay_loam")
        self.assertEqual(str(response.data["ph"]), "7.80")
        self.assertEqual(str(response.data["nitrogen_ppm"]), "22.50")
        self.assertEqual(response.data["sample_date"], "2026-03-15")
        self.assertTrue(response.data["irrigation_available"])
        self.assertEqual(response.data["water_reliability"], "seasonal_variable")
        self.assertAlmostEqual(response.data["priorities"]["water_conservation"], 0.4)
        self.assertEqual(
            response.data["constraints"]["equipment"], ["no_mechanized_harvester"]
        )
        self.assertEqual(len(response.data["current_crops"]), 2)
        self.assertEqual(response.data["current_crops"][0]["season"], "Winter 2025/26")
        self.assertEqual(response.data["current_crops"][0]["crop"], "Wheat")
        self.assertEqual(response.data["current_crops"][0]["source"], "FARMER_REPORTED")

    def test_partial_update_keeps_other_fields(self) -> None:
        self.client.patch(self.url, {"ph": "6.50", "texture_class": "loam"}, format="json")
        response = self.client.patch(self.url, {"irrigation_type": "drip"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(str(response.data["ph"]), "6.50")
        self.assertEqual(response.data["texture_class"], "loam")
        self.assertEqual(response.data["irrigation_type"], "drip")

    def test_crops_are_replaced_on_update(self) -> None:
        self.client.patch(
            self.url,
            {"current_crops": [{"season": "Winter 2025/26", "crop": "Wheat"}]},
            format="json",
        )
        response = self.client.patch(
            self.url,
            {"current_crops": [{"season": "Summer 2026", "crop": "Rice"}]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["current_crops"]), 1)
        self.assertEqual(response.data["current_crops"][0]["crop"], "Rice")

    def test_unknown_values_remain_null(self) -> None:
        response = self.client.patch(
            self.url, {"ph": None, "texture_class": "", "nitrogen_ppm": None}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNone(response.data["ph"])
        self.assertIsNone(response.data["nitrogen_ppm"])

    def test_invalid_ph_is_rejected(self) -> None:
        response = self.client.patch(self.url, {"ph": "14.50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ph", response.data)

    def test_priorities_must_sum_to_one(self) -> None:
        response = self.client.patch(
            self.url, {"priorities": {"water_conservation": 0.9, "soil_regeneration": 0.5}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("priorities", response.data)

    def test_negative_priority_is_rejected(self) -> None:
        response = self.client.patch(
            self.url, {"priorities": {"water_conservation": -0.5, "soil_regeneration": 1.5}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_priority_key_is_rejected(self) -> None:
        response = self.client.patch(
            self.url, {"priorities": {"yield_max": 1.0}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_constraint_key_is_rejected(self) -> None:
        response = self.client.patch(
            self.url, {"constraints": {"budget": "low"}}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_provenance_values_are_validated(self) -> None:
        response = self.client.patch(self.url, {"soil_source": "MADE_UP"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("soil_source", response.data)

    def test_put_replaces_context(self) -> None:
        response = self.client.put(
            self.url,
            {
                "soil_source": "REMOTE_SENSING",
                "texture_class": "sandy_loam",
                "priorities": {"water_conservation": 1.0},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["soil_source"], "REMOTE_SENSING")
        self.assertEqual(response.data["texture_class"], "sandy_loam")
