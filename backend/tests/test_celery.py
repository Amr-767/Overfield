"""Celery configuration and task-wiring tests (Phase 1D).

These tests do not require a running broker or worker: they assert the app is
configured from Django settings and run the probe task in-process.
"""

from celery import Celery
from django.conf import settings
from django.test import SimpleTestCase

from apps.core import tasks as core_tasks
from config.celery import app


class CeleryConfigurationTests(SimpleTestCase):
    def test_app_is_a_configured_celery_instance(self) -> None:
        self.assertIsInstance(app, Celery)
        self.assertEqual(app.main, "agrospace")

    def test_broker_and_result_backend_use_redis(self) -> None:
        self.assertTrue(str(app.conf.broker_url).startswith("redis://"))
        self.assertTrue(str(app.conf.result_backend).startswith("redis://"))

    def test_broker_uses_configured_redis_host_and_port(self) -> None:
        broker = str(app.conf.broker_url)
        self.assertIn(settings.REDIS_HOST, broker)
        self.assertIn(str(settings.REDIS_PORT), broker)

    def test_serialization_is_json_only(self) -> None:
        self.assertEqual(app.conf.task_serializer, "json")
        self.assertEqual(app.conf.result_serializer, "json")
        self.assertEqual(app.conf.accept_content, ["json"])

    def test_timezone_matches_django(self) -> None:
        self.assertEqual(str(app.conf.timezone), settings.TIME_ZONE)


class CeleryTaskDiscoveryTests(SimpleTestCase):
    def test_ping_task_is_registered(self) -> None:
        self.assertIn("core.ping", app.tasks)

    def test_ping_task_runs_in_process_and_returns_pong(self) -> None:
        result = core_tasks.ping.apply()
        self.assertTrue(result.successful())
        self.assertEqual(result.get(), "pong")
