"""Registration, JWT authentication and profile endpoints."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import FarmerProfile

User = get_user_model()

STRONG_PASSWORD = "AgroSpace!2026pass"


class RegistrationTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_register_creates_user_and_profile(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "username": "farmer1",
                "email": "farmer1@example.com",
                "password": STRONG_PASSWORD,
                "display_name": "Ahmed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["username"], "farmer1")
        self.assertEqual(response.data["display_name"], "Ahmed")
        self.assertNotIn("password", response.data)

        user = User.objects.get(username="farmer1")
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertTrue(FarmerProfile.objects.filter(user=user, display_name="Ahmed").exists())

    def test_duplicate_username_is_rejected(self) -> None:
        User.objects.create_user(username="farmer1", password=STRONG_PASSWORD)
        response = self.client.post(
            "/api/v1/auth/register/",
            {"username": "farmer1", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_weak_password_is_rejected(self) -> None:
        response = self.client.post(
            "/api/v1/auth/register/",
            {"username": "farmer2", "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)


class AuthenticationTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="farmer1", email="farmer1@example.com", password=STRONG_PASSWORD
        )
        FarmerProfile.objects.create(user=self.user, display_name="Ahmed")

    def _login(self) -> str:
        response = self.client.post(
            "/api/v1/auth/token/",
            {"username": "farmer1", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        return response.data["access"]

    def test_token_pair_and_refresh(self) -> None:
        access = self._login()
        refresh = self.client.post(
            "/api/v1/auth/token/",
            {"username": "farmer1", "password": STRONG_PASSWORD},
            format="json",
        ).data["refresh"]

        refreshed = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access", refreshed.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get("/api/v1/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)

    def test_me_requires_authentication(self) -> None:
        self.assertEqual(self.client.get("/api/v1/me/").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile(self) -> None:
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get("/api/v1/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "farmer1")
        self.assertEqual(response.data["display_name"], "Ahmed")
        self.assertEqual(response.data["email"], "farmer1@example.com")

    def test_me_patch_updates_display_name_and_email(self) -> None:
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.patch(
            "/api/v1/me/",
            {"display_name": "Ahmed Hassan", "email": "ahmed@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["display_name"], "Ahmed Hassan")
        self.assertEqual(response.data["email"], "ahmed@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ahmed@example.com")

    def test_me_patch_rejects_email_taken_by_another_user(self) -> None:
        User.objects.create_user(username="other", email="taken@example.com", password=STRONG_PASSWORD)
        access = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.patch("/api/v1/me/", {"email": "taken@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_token_is_rejected(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")
        self.assertEqual(self.client.get("/api/v1/me/").status_code, status.HTTP_401_UNAUTHORIZED)
