"""Indicator contract shared by all four Phase 4 gauges (ADR-022).

Every indicator returns the same envelope so the API and UI never need
gauge-specific parsing:

* a **status** that says whether the calculation was possible at all;
* **measurements** that are physical values with units and provenance;
* explicit **coverage** (expected vs covered days) and **freshness**;
* the **sources** and **methodology** that produced the numbers;
* an explicit **missing** list explaining what could not be assessed.

``score`` is always ``None`` in Phase 4 (decision R14): no 0–100 numbers are
invented without a documented, crop-aware rubric.

Design rules (approved in Phase 4A):
- missing observations are never converted to zero;
- confidence is coverage-based and capped by source/spatial quality;
- freshness is separate from confidence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping


class IndicatorStatus(StrEnum):
    """Whether an indicator could be computed."""

    OK = "OK"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_ASSESSED = "NOT_ASSESSED"
    UNAVAILABLE = "UNAVAILABLE"


class Confidence(StrEnum):
    """Confidence in the *presented* indicator, from observation coverage."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Freshness(StrEnum):
    """Operational age of the newest observation used (not a data-quality claim)."""

    FRESH = "FRESH"
    RECENT = "RECENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    # Soil sample-age labels (ADR-023 / R17); not used by water or heat.
    AGEING = "AGEING"
    FUTURE = "FUTURE"


class DriverDirection(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class Coverage:
    """Expected vs observed days for a window.

    ``days_covered`` is the number of days that carry a usable value for the
    calling indicator. For multi-parameter indicators it is the *minimum*
    across parameters, and ``by_parameter`` keeps the detail.
    """

    days_expected: int
    days_covered: int
    by_parameter: Mapping[str, int] = field(default_factory=dict)

    @property
    def days_missing(self) -> int:
        return max(0, self.days_expected - self.days_covered)

    @property
    def ratio(self) -> Decimal:
        if self.days_expected <= 0:
            return Decimal("0")
        return (Decimal(self.days_covered) / Decimal(self.days_expected)).quantize(
            Decimal("0.0001")
        )

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "days_expected": self.days_expected,
            "days_covered": self.days_covered,
            "days_missing": self.days_missing,
            "ratio": _decimal_str(self.ratio),
        }
        if self.by_parameter:
            payload["by_parameter"] = dict(self.by_parameter)
        return payload


@dataclass(frozen=True, slots=True)
class Completeness:
    """Property completeness for indicators that are not a daily time series."""

    properties_expected: int
    properties_present: int

    @property
    def ratio(self) -> Decimal:
        if self.properties_expected <= 0:
            return Decimal("0")
        return (Decimal(self.properties_present) / Decimal(self.properties_expected)).quantize(
            Decimal("0.0001")
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "properties_expected": self.properties_expected,
            "properties_present": self.properties_present,
            "ratio": _decimal_str(self.ratio),
        }


@dataclass(frozen=True, slots=True)
class Period:
    """The analysed window and how old its newest observation is."""

    start: date
    end: date
    latest_observation: date | None
    age_days: int | None
    freshness: Freshness

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "latest_observation": (
                self.latest_observation.isoformat() if self.latest_observation else None
            ),
            "age_days": self.age_days,
            "freshness": self.freshness.value,
        }


@dataclass(frozen=True, slots=True)
class Measurement:
    """A physical value with its unit and provenance."""

    name: str
    value: Decimal | int | str | None
    unit: str
    source: str | None = None
    parameter: str | None = None
    product: str | None = None
    quality: str = "AVAILABLE"
    method: str = ""
    interpretation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": _json_value(self.value),
            "unit": self.unit,
            "source": self.source,
            "parameter": self.parameter,
            "product": self.product,
            "quality": self.quality,
            "method": self.method,
            "interpretation": self.interpretation,
        }


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Where a measurement came from, with the provider's own metadata."""

    provider: str
    parameter: str
    units: str
    product: str
    data_category: str
    native_resolution_note: str
    time_standard: str
    access_date: date | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "parameter": self.parameter,
            "units": self.units,
            "product": self.product,
            "data_category": self.data_category,
            "native_resolution_note": self.native_resolution_note or None,
            "time_standard": self.time_standard,
            "access_date": self.access_date.isoformat() if self.access_date else None,
        }


@dataclass(frozen=True, slots=True)
class MissingInput:
    """Something we deliberately could not assess, and why it matters."""

    name: str
    impact: str
    required_for: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "impact": self.impact, "required_for": self.required_for}


@dataclass(frozen=True, slots=True)
class Driver:
    """A short, farmer-readable reason behind the indicator."""

    name: str
    direction: DriverDirection
    value: Decimal | int | str | None = None
    unit: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction.value,
            "value": _json_value(self.value),
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class Methodology:
    """Identifies the rule set so results are reproducible."""

    id: str
    version: str
    description: str
    threshold_source: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "threshold_source": self.threshold_source,
        }


@dataclass(frozen=True, slots=True)
class IndicatorResult:
    """Uniform envelope returned by every indicator service."""

    code: str
    label: str
    status: IndicatorStatus
    confidence: Confidence
    period: Period | None
    coverage: Coverage | None
    summary: str
    measurements: tuple[Measurement, ...] = ()
    context: tuple[Measurement, ...] = ()
    drivers: tuple[Driver, ...] = ()
    missing: tuple[MissingInput, ...] = ()
    methodology: Methodology = field(
        default_factory=lambda: Methodology(id="unknown", version="0", description="")
    )
    sources: tuple[SourceReference, ...] = ()
    limitations: tuple[str, ...] = ()
    completeness: Completeness | None = None
    # Decision R14: no 0–100 scores in Phase 4.
    score: None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "status": self.status.value,
            "score": None,
            "confidence": self.confidence.value,
            "as_of": (
                self.period.latest_observation.isoformat()
                if self.period and self.period.latest_observation
                else None
            ),
            "period": self.period.as_dict() if self.period else None,
            "coverage": self.coverage.as_dict() if self.coverage else None,
            "completeness": self.completeness.as_dict() if self.completeness else None,
            "summary": self.summary,
            "measurements": [item.as_dict() for item in self.measurements],
            "context": [item.as_dict() for item in self.context],
            "drivers": [item.as_dict() for item in self.drivers],
            "missing": [item.as_dict() for item in self.missing],
            "methodology": self.methodology.as_dict(),
            "sources": [item.as_dict() for item in self.sources],
            "limitations": list(self.limitations),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


def _decimal_str(value: Decimal) -> str:
    return format(value, "f")


def _json_value(value: Any) -> Any:
    """JSON-safe rendering: Decimals stay strings to preserve precision."""
    if isinstance(value, Decimal):
        return _decimal_str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


__all__ = [
    "Completeness",
    "Confidence",
    "Coverage",
    "Driver",
    "DriverDirection",
    "Freshness",
    "IndicatorResult",
    "IndicatorStatus",
    "Measurement",
    "Methodology",
    "MissingInput",
    "Period",
    "SourceReference",
]
