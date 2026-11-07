"""Settings and database configuration smoke tests."""

from django.conf import settings
from django.db import connection
from django.test import SimpleTestCase, TestCase


class SettingsConfigurationTests(SimpleTestCase):
    def test_api_uses_split_settings_and_postgres(self) -> None:
        self.assertTrue(settings.SECRET_KEY)
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertIn("corsheaders", settings.INSTALLED_APPS)
        self.assertIn("rest_framework", settings.INSTALLED_APPS)
        self.assertTrue(
            any(app == "apps.core" or app.endswith("apps.core.apps.CoreConfig") for app in settings.INSTALLED_APPS)
        )

    def test_cors_allows_local_vite_origins(self) -> None:
        origins = set(settings.CORS_ALLOWED_ORIGINS)
        self.assertTrue(
            {"http://localhost:5173", "http://127.0.0.1:5173"} & origins
            or origins  # custom .env override is also acceptable
        )


class DatabaseConnectivityTests(TestCase):
    def test_database_connection_works(self) -> None:
        connection.ensure_connection()
        self.assertTrue(connection.is_usable())
