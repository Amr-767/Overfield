"""Celery application for Overfield (Phase 1D).

Redis is provided by the existing Phase 1A Docker Compose stack; this module
only wires Celery to that broker. No domain or NASA tasks are defined here.
"""

from __future__ import annotations

import os

from celery import Celery

# Allow `celery -A config worker` to run from `backend/` without extra flags.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("agrospace")

# Broker/result configuration lives in Django settings (CELERY_* keys).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover a `tasks.py` module in every installed app.
app.autodiscover_tasks()
