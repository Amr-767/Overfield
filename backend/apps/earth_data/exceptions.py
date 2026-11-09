"""Application-level exceptions for Earth data providers (Phase 3).

These wrap transport, protocol and payload problems so callers (Celery tasks,
services) never see ``urllib``/``http.client``/``json`` internals and can react
to a stable, small set of failure categories.
"""

from __future__ import annotations

from typing import Iterable


class PowerError(Exception):
    """Base class for every NASA POWER failure."""

    code = "power_error"
    retryable = False

    def __init__(self, message: str, *, details: Iterable[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: tuple[str, ...] = tuple(details or ())

    def as_dict(self) -> dict[str, object]:
        """Serialisable form for job records and API responses."""
        payload: dict[str, object] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = list(self.details)
        return payload


class PowerConfigurationError(PowerError):
    """The request we were asked to make is invalid; nothing was sent."""

    code = "power_configuration_error"


class PowerRequestError(PowerError):
    """POWER understood the request and refused it (permanent 4xx)."""

    code = "power_request_error"


class PowerTransientError(PowerError):
    """A retryable failure persisted after the allowed attempts."""

    code = "power_transient_error"
    retryable = True


class PowerResponseError(PowerError):
    """POWER answered, but the payload is unusable or contradicts the request."""

    code = "power_response_error"


__all__ = [
    "PowerError",
    "PowerConfigurationError",
    "PowerRequestError",
    "PowerTransientError",
    "PowerResponseError",
]
