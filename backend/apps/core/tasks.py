"""Minimal foundation tasks (Phase 1D).

Deliberately tiny: this proves the worker/broker wiring works. NASA ingestion,
raster processing, and domain tasks arrive in later phases.
"""

from __future__ import annotations

from celery import shared_task


@shared_task(name="core.ping")
def ping() -> str:
    """Return a constant so the worker and broker can be verified end to end."""
    return "pong"
