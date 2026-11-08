"""Ownership isolation: one farmer must never read or change another's data."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.farms.models import Farm, FarmerContext

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


class FarmOwnershipTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="owner", password="AgroSpace!2026pass")
        self.other = User.objects.create_user(username="other", password="AgroSpace!2026pass")

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        created = self.owner_client.post(
            "/api/v1/farms/",
            {"name": "Owner Farm", "boundary": POLYGON},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.farm_id = created.data["id"]

        self.other_client = APIClient()
        self.other_client.force_authenticate(self.other)

    def test_other_user_list_is_empty(self) -> None:
        response = self.other_client.get("/api/v1/farms/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_other_user_cannot_retrieve(self) -> None:
        response = self.other_client.get(f"/api/v1/farms/{self.farm_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_update(self) -> None:
        response = self.other_client.patch(
            f"/api/v1/farms/{self.farm_id}/", {"name": "Hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Farm.objects.get(pk=self.farm_id).name, "Owner Farm")

    def test_other_user_cannot_delete(self) -> None:
        response = self.other_client.delete(f"/api/v1/farms/{self.farm_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Farm.objects.filter(pk=self.farm_id).exists())

    def test_other_user_cannot_read_context(self) -> None:
        FarmerContext.objects.get_or_create(farm_id=self.farm_id)
        response = self.other_client.get(f"/api/v1/farms/{self.farm_id}/context/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_write_context(self) -> None:
        response = self.other_client.patch(
            f"/api/v1/farms/{self.farm_id}/context/", {"ph": "6.50"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_create_zone(self) -> None:
        response = self.other_client.post(
            f"/api/v1/farms/{self.farm_id}/zones/",
            {"name": "Intrusion", "boundary": POLYGON},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_read_own_farm(self) -> None:
        response = self.owner_client.get(f"/api/v1/farms/{self.farm_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Farm.objects.get(pk=self.farm_id).owner, self.owner)
