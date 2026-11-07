"""Health-check endpoint tests."""

from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_health_endpoint_returns_healthy_when_database_is_up(self) -> None:
        response = self.client.get(reverse("api-v1:health"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["status"], "healthy")
        self.assertEqual(payload["database"], "connected")
        self.assertIn("timestamp", payload)

    def test_health_endpoint_is_public(self) -> None:
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")

    def test_health_endpoint_reports_503_when_database_is_down(self) -> None:
        with patch(
            "django.db.connection.ensure_connection",
            side_effect=OperationalError("database is down"),
        ):
            response = self.client.get(reverse("api-v1:health"))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        payload = response.json()
        self.assertEqual(payload["status"], "unhealthy")
        self.assertEqual(payload["database"], "unavailable")
        self.assertIn("timestamp", payload)
