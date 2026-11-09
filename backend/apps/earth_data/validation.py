"""Validation helpers for the environmental data endpoints (Phase 3E).

Kept out of the views so the same rules apply to observation queries and scan
requests, and so they can be unit-tested directly.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Sequence

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.earth_data.models import DatasetSource, Provider
from apps.earth_data.providers.power import MAX_PARAMETERS_PER_REQUEST, MINIMUM_SERVICE_DATE

DEFAULT_MAX_RANGE_DAYS = 366


def max_range_days() -> int:
    return int(getattr(settings, "NASA_FETCH_MAX_RANGE_DAYS", DEFAULT_MAX_RANGE_DAYS))


def active_sources() -> dict[str, DatasetSource]:
    """Catalogue rows that may be requested through the API."""
    return {
        source.parameter_code: source
        for source in DatasetSource.objects.filter(provider=Provider.NASA_POWER, is_active=True)
    }


def supported_parameter_codes() -> list[str]:
    return sorted(active_sources())


def normalise_parameters(raw: Iterable[str] | str | None) -> tuple[str, ...]:
    """Split comma-separated and repeated values, upper-case and de-duplicate."""
    if raw is None:
        return ()
    if isinstance(raw, str):
        items: Sequence[str] = [raw]
    else:
        items = list(raw)

    codes: list[str] = []
    for item in items:
        for part in str(item).split(","):
            code = part.strip().upper()
            if code and code not in codes:
                codes.append(code)
    return tuple(codes)


def validate_parameters(codes: Sequence[str]) -> tuple[str, ...]:
    """Reject unknown or retired parameter codes with the supported list."""
    if len(codes) > MAX_PARAMETERS_PER_REQUEST:
        raise ValidationError(
            {
                "parameter": [
                    f"At most {MAX_PARAMETERS_PER_REQUEST} parameters may be requested at once "
                    f"(got {len(codes)})."
                ]
            }
        )

    supported = active_sources()
    unknown = [code for code in codes if code not in supported]
    if unknown:
        raise ValidationError(
            {
                "parameter": [
                    f"Unsupported parameter(s): {', '.join(unknown)}. "
                    f"Supported: {', '.join(sorted(supported))}."
                ]
            }
        )
    return tuple(codes)


def validate_date_range(
    start: date,
    end: date,
    *,
    parameters: Sequence[str],
    today: date | None = None,
) -> tuple[date, date]:
    """Enforce ordering, the maximum window, and provider availability."""
    today = today or date.today()

    if start > end:
        raise ValidationError(
            {"start": [f"start ({start.isoformat()}) must not be after end ({end.isoformat()})."]}
        )

    window_days = (end - start).days + 1
    limit = max_range_days()
    if window_days > limit:
        raise ValidationError(
            {
                "end": [
                    f"Requested window is {window_days} days; the maximum is {limit} days. "
                    "Narrow the range."
                ]
            }
        )

    if start < MINIMUM_SERVICE_DATE:
        raise ValidationError(
            {
                "start": [
                    f"NASA POWER daily data starts on {MINIMUM_SERVICE_DATE.isoformat()}."
                ]
            }
        )

    if end > today:
        raise ValidationError({"end": ["end must not be in the future."]})

    sources = active_sources()
    for code in parameters:
        source = sources.get(code)
        if source and start < source.first_available_date:
            raise ValidationError(
                {
                    "start": [
                        f"Parameter {code} is only available from "
                        f"{source.first_available_date.isoformat()}."
                    ]
                }
            )

    return start, end


__all__ = [
    "DEFAULT_MAX_RANGE_DAYS",
    "active_sources",
    "max_range_days",
    "normalise_parameters",
    "supported_parameter_codes",
    "validate_date_range",
    "validate_parameters",
]
