"""Farm CRUD, boundary handling, area calculation and zone API tests."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.farms.models import Farm

User = get_user_model()

KNOWN_POLYGON = {
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

SMALL_ZONE = {
    "type": "Polygon",
    "coordinates": [
        [
            [30.9505, 30.7905],
            [30.9510, 30.7905],
            [30.9510, 30.7910],
            [30.9505, 30.7910],
            [30.9505, 30.7905],
        ]
    ],
}

OUTSIDE_ZONE = {
    "type": "Polygon",
    "coordinates": [
        [
            [31.5000, 31.5000],
            [31.5010, 31.5000],
            [31.5010, 31.5010],
            [31.5000, 31.5010],
            [31.5000, 31.5000],
        ]
    ],
}


class FarmApiTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username="farmer1", password="AgroSpace!2026pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _create_farm(self, **overrides) -> dict:
        payload = {
            "name": "North Field",
            "country_code": "EG",
            "region_code": "eg-gharbia",
            "timezone": "Africa/Cairo",
            "boundary": KNOWN_POLYGON,
        }
        payload.update(overrides)
        response = self.client.post("/api/v1/farms/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response.data

    def test_create_farm_with_polygon(self) -> None:
        data = self._create_farm()
        self.assertEqual(data["name"], "North Field")
        self.assertEqual(data["boundary"]["type"], "MultiPolygon")
        self.assertAlmostEqual(Decimal(data["area_hectares"]), Decimal("3.7882"), delta=Decimal("0.01"))
        self.assertEqual(data["area_source"], Farm.AreaSource.GEOMETRY_DERIVED)
        self.assertEqual(data["geometry_source"], Farm.GeometrySource.BOUNDARY)
        self.assertEqual(data["spatial_precision"], "HIGH")
        # Marker centroid uses [lon, lat] ordering.
        self.assertAlmostEqual(data["location"]["coordinates"][0], 30.95115, places=5)
        self.assertAlmostEqual(data["location"]["coordinates"][1], 30.79095, places=5)
        self.assertIsNotNone(data["created_at"])
        self.assertIsNotNone(data["updated_at"])

    def test_client_supplied_area_is_ignored(self) -> None:
        data = self._create_farm(area_hectares="999999.0000")
        self.assertAlmostEqual(Decimal(data["area_hectares"]), Decimal("3.7882"), delta=Decimal("0.01"))

    def test_polygon_feature_is_accepted(self) -> None:
        data = self._create_farm(
            boundary={"type": "Feature", "properties": {}, "geometry": KNOWN_POLYGON}
        )
        self.assertEqual(data["boundary"]["type"], "MultiPolygon")

    def test_invalid_polygon_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/farms/",
            {
                "name": "Broken",
                "boundary": {
                    "type": "Polygon",
                    "coordinates": [[[30.95, 30.79], [30.96, 30.79], [30.96, 30.80], [30.95, 30.80]]],
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("boundary", response.data)
        self.assertIn("not closed", str(response.data["boundary"]))

    def test_geometry_with_missing_boundary_and_location_is_rejected(self) -> None:
        response = self.client.post("/api/v1/farms/", {"name": "Nothing"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("boundary", response.data)

    def test_location_only_farm_uses_reported_area(self) -> None:
        response = self.client.post(
            "/api/v1/farms/",
            {
                "name": "Point Farm",
                "location": {"type": "Point", "coordinates": [30.95, 30.79]},
                "farmer_reported_area_hectares": "2.5000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["boundary"])
        self.assertEqual(Decimal(response.data["area_hectares"]), Decimal("2.5000"))
        self.assertEqual(response.data["area_source"], Farm.AreaSource.FARMER_REPORTED)
        self.assertEqual(response.data["geometry_source"], Farm.GeometrySource.LOCATION_POINT)
        self.assertEqual(response.data["spatial_precision"], "LOW")

    def test_location_only_farm_requires_reported_area(self) -> None:
        response = self.client.post(
            "/api/v1/farms/",
            {"name": "Point Farm", "location": {"type": "Point", "coordinates": [30.95, 30.79]}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("farmer_reported_area_hectares", response.data)

    def test_list_and_retrieve_farm(self) -> None:
        created = self._create_farm()
        listing = self.client.get("/api/v1/farms/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["id"], created["id"])

        detail = self.client.get(f"/api/v1/farms/{created['id']}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["name"], "North Field")

    def test_patch_metadata_keeps_computed_area(self) -> None:
        created = self._create_farm()
        response = self.client.patch(
            f"/api/v1/farms/{created['id']}/", {"name": "South Field"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["name"], "South Field")
        self.assertAlmostEqual(Decimal(response.data["area_hectares"]), Decimal("3.7882"), delta=Decimal("0.01"))

    def test_patch_boundary_recomputes_area(self) -> None:
        created = self._create_farm()
        smaller = {
            "type": "Polygon",
            "coordinates": [
                [
                    [30.9501, 30.7901],
                    [30.9511, 30.7901],
                    [30.9511, 30.7909],
                    [30.9501, 30.7909],
                    [30.9501, 30.7901],
                ]
            ],
        }
        response = self.client.patch(
            f"/api/v1/farms/{created['id']}/", {"boundary": smaller}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotAlmostEqual(
            Decimal(response.data["area_hectares"]), Decimal("3.7882"), places=2
        )

    def test_delete_farm(self) -> None:
        created = self._create_farm()
        response = self.client.delete(f"/api/v1/farms/{created['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Farm.objects.filter(pk=created["id"]).exists())

    def test_validate_boundary_endpoint_reports_area(self) -> None:
        response = self.client.post(
            "/api/v1/farms/validate-boundary/", {"boundary": KNOWN_POLYGON}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["srid"], 4326)
        self.assertAlmostEqual(Decimal(response.data["area_hectares"]), Decimal("3.7882"), delta=Decimal("0.01"))

    def test_validate_boundary_endpoint_rejects_invalid_geometry(self) -> None:
        response = self.client.post(
            "/api/v1/farms/validate-boundary/",
            {"boundary": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_zone_inside_farm(self) -> None:
        farm = self._create_farm()
        response = self.client.post(
            f"/api/v1/farms/{farm['id']}/zones/",
            {"name": "North strip", "boundary": SMALL_ZONE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["name"], "North strip")
        self.assertEqual(response.data["boundary"]["type"], "MultiPolygon")
        self.assertGreater(Decimal(response.data["area_hectares"]), Decimal("0"))

        listing = self.client.get(f"/api/v1/farms/{farm['id']}/zones/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)

    def test_zone_outside_farm_is_rejected(self) -> None:
        farm = self._create_farm()
        response = self.client.post(
            f"/api/v1/farms/{farm['id']}/zones/",
            {"name": "Elsewhere", "boundary": OUTSIDE_ZONE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("boundary", response.data)


class FarmAuthenticationTests(TestCase):
    def test_farm_endpoints_require_authentication(self) -> None:
        client = APIClient()
        self.assertEqual(client.get("/api/v1/farms/").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(client.post("/api/v1/farms/", {}, format="json").status_code, status.HTTP_401_UNAUTHORIZED)
