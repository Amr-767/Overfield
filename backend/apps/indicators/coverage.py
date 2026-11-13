"""Coverage, freshness and confidence helpers (Phase 4B).

Approved rules (R14/R15 corrections):

* Confidence bands do not overlap: ``NONE = 0``, ``LOW = (0, 60)``,
  ``MEDIUM = [60, 95)``, ``HIGH = [95, 100]`` (percent).
* Confidence is capped by the *quality of the source*: grid-cell reanalysis
  values cannot yield HIGH confidence about a specific field.
* Freshness is independent from confidence.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable, Mapping

from django.conf import settings

from .contract import Confidence, Coverage, Freshness, Period

CONFIDENCE_MEDIUM_THRESHOLD = Decimal("0.60")
CONFIDENCE_HIGH_THRESHOLD = Decimal("0.95")

DEFAULT_DEFAULT_WINDOW_DAYS = 30
DEFAULT_MAX_WINDOW_DAYS = 366
DEFAULT_FRESH_DAYS = 7
DEFAULT_RECENT_DAYS = 30
# A MERRA-2 cell is a 0.5 x 0.625 degree estimate, not a field measurement.
GRID_CELL_CONFIDENCE_CAP = Confidence.MEDIUM


def _setting(name: str, fallback):
    return getattr(settings, name, fallback)


def default_window_days() -> int:
    return int(_setting("INDICATOR_DEFAULT_WINDOW_DAYS", DEFAULT_DEFAULT_WINDOW_DAYS))


def max_window_days() -> int:
    return int(_setting("INDICATOR_MAX_WINDOW_DAYS", DEFAULT_MAX_WINDOW_DAYS))


def fresh_max_days() -> int:
    return int(_setting("INDICATOR_FRESH_MAX_DAYS", DEFAULT_FRESH_DAYS))


def recent_max_days() -> int:
    return int(_setting("INDICATOR_RECENT_MAX_DAYS", DEFAULT_RECENT_DAYS))


def as_decimal(value, fallback: str) -> Decimal:
    """Read a numeric setting/argument as Decimal without binary-float drift."""
    if value is None:
        return Decimal(fallback)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Cannot interpret {value!r} as a decimal.") from exc


def confidence_for(
    coverage_ratio: Decimal,
    *,
    cap: Confidence | None = None,
) -> Confidence:
    """Map a coverage ratio (0..1) to a confidence band, then apply ``cap``."""
    ratio = max(Decimal("0"), min(Decimal("1"), coverage_ratio))
    if ratio <= 0:
        band = Confidence.NONE
    elif ratio < CONFIDENCE_MEDIUM_THRESHOLD:
        band = Confidence.LOW
    elif ratio < CONFIDENCE_HIGH_THRESHOLD:
        band = Confidence.MEDIUM
    else:
        band = Confidence.HIGH

    if cap is None:
        return band
    order = {Confidence.NONE: 0, Confidence.LOW: 1, Confidence.MEDIUM: 2, Confidence.HIGH: 3}
    return band if order[band] <= order[cap] else cap


def freshness_for(
    age_days: int | None,
    *,
    fresh_days: int | None = None,
    recent_days: int | None = None,
) -> Freshness:
    """Classify the age of the newest observation."""
    if age_days is None:
        return Freshness.UNKNOWN
    fresh_limit = fresh_max_days() if fresh_days is None else fresh_days
    recent_limit = recent_max_days() if recent_days is None else recent_days
    if age_days <= fresh_limit:
        return Freshness.FRESH
    if age_days <= recent_limit:
        return Freshness.RECENT
    return Freshness.STALE


def build_period(
    *,
    start: date,
    end: date,
    latest_observation: date | None,
    today: date,
) -> Period:
    """Assemble the analysed window and its freshness metadata."""
    age_days = (today - latest_observation).days if latest_observation else None
    return Period(
        start=start,
        end=end,
        latest_observation=latest_observation,
        age_days=age_days,
        freshness=freshness_for(age_days),
    )


def count_days(start: date, end: date) -> int:
    """Inclusive day count for a window (0 when the window is inverted)."""
    if end < start:
        return 0
    return (end - start).days + 1


def days_in_window(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count_days(start, end))]


def coverage_from_values(
    start: date,
    end: date,
    values: Mapping[date, Decimal | None],
    *,
    parameter: str | None = None,
) -> Coverage:
    """Coverage for one parameter: days with a non-null value inside the window."""
    covered = sum(
        1 for day in days_in_window(start, end) if values.get(day) is not None
    )
    return Coverage(
        days_expected=count_days(start, end),
        days_covered=covered,
        by_parameter={parameter: covered} if parameter else {},
    )


def combine_coverage(expected: int, by_parameter: Mapping[str, int]) -> Coverage:
    """Headline coverage = the weakest parameter, with per-parameter detail kept."""
    covered = min(by_parameter.values()) if by_parameter else 0
    return Coverage(days_expected=expected, days_covered=covered, by_parameter=dict(by_parameter))


def latest_window(observed_dates: Iterable[date], window_days: int) -> tuple[date, date] | None:
    """The window ends at the newest observation and spans ``window_days``.

    Approved convention: the window describes the latest available observation
    period, never "today's weather".
    """
    dates = list(observed_dates)
    if not dates:
        return None
    span = max(1, int(window_days))
    end = max(dates)
    return end - timedelta(days=span - 1), end


__all__ = [
    "CONFIDENCE_HIGH_THRESHOLD",
    "CONFIDENCE_MEDIUM_THRESHOLD",
    "GRID_CELL_CONFIDENCE_CAP",
    "as_decimal",
    "build_period",
    "combine_coverage",
    "confidence_for",
    "count_days",
    "coverage_from_values",
    "days_in_window",
    "default_window_days",
    "freshness_for",
    "latest_window",
    "max_window_days",
]
