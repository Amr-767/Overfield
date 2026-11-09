"""Earth data providers (Phase 3).

Currently only NASA POWER. The factory reads Django settings so callers never
construct transports or hardcode timeouts.
"""

from __future__ import annotations

from functools import lru_cache

from .power import PowerClient
from .power_transport import HttpPowerTransport

DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
DEFAULT_READ_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_SECONDS = 0.5
DEFAULT_MAX_RETRY_AFTER_SECONDS = 30.0
DEFAULT_CACHE_TTL_SECONDS = 900.0


@lru_cache(maxsize=1)
def get_power_client() -> PowerClient:
    """Return the process-wide NASA POWER client, configured from settings.

    Imported lazily so tests can construct ``PowerClient`` with a fake transport
    without touching Django settings.
    """
    from django.conf import settings

    base_url = getattr(settings, "NASA_POWER_BASE_URL", None)
    connect_timeout = float(
        getattr(settings, "NASA_POWER_CONNECT_TIMEOUT_SECONDS", DEFAULT_CONNECT_TIMEOUT_SECONDS)
    )
    read_timeout = float(
        getattr(
            settings,
            "NASA_POWER_READ_TIMEOUT_SECONDS",
            getattr(settings, "NASA_POWER_TIMEOUT_SECONDS", DEFAULT_READ_TIMEOUT_SECONDS),
        )
    )
    max_retries = int(getattr(settings, "NASA_POWER_MAX_RETRIES", DEFAULT_MAX_RETRIES))
    cache_ttl = float(getattr(settings, "NASA_POWER_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS))
    backoff = float(getattr(settings, "NASA_POWER_BACKOFF_SECONDS", DEFAULT_BACKOFF_SECONDS))
    max_retry_after = float(
        getattr(settings, "NASA_POWER_MAX_RETRY_AFTER_SECONDS", DEFAULT_MAX_RETRY_AFTER_SECONDS)
    )

    transport = HttpPowerTransport(connect_timeout=connect_timeout, read_timeout=read_timeout)
    kwargs = {
        "transport": transport,
        "max_retries": max_retries,
        "backoff_seconds": backoff,
        "max_retry_after_seconds": max_retry_after,
        "cache_ttl_seconds": cache_ttl,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return PowerClient(**kwargs)


__all__ = ["get_power_client"]
