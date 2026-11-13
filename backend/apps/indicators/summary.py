"""Environmental summary orchestration (Phase 4D).

Combines the four indicator services into one response. The view stays thin:
it resolves the farm, validates ``window_days`` and calls
:func:`build_environment_summary`.

Definition of "current" (approved): the window ends at the **latest available
observation**, never at "today". Age and freshness are reported so stale data is
obvious, and no real-time claim is made.

Query budget (owner request, no observations cached):
1. farm lookup (owner-filtered, in the view)
2. latest observation date (aggregate)
3. all parameter values for the window (single query)
4. dataset source metadata (single query)
5. farmer context (single query)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Mapping

from django.utils import timezone

from apps.earth_data.providers.power import RECOMMENDED_PARAMETERS
from apps.farms.models import Farm, FarmerContext

from .contract import (
    Confidence,
    Freshness,
    IndicatorResult,
    IndicatorStatus,
    Measurement,
    Period,
)
from .coverage import default_window_days, freshness_for, max_window_days
from .selectors import (
    latest_observation_date,
    soil_profile_from_context,
    source_references,
    window_series,
)
from .services.heat import calculate_heat_indicator
from .services.market import calculate_market_indicator
from .services.soil import calculate_soil_indicator
from .services.water import calculate_water_indicator

WATER_PARAMETER = "PRECTOTCORR"
HEAT_PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN")

TOP_LEVEL_LIMITATIONS = (
    "Indicators describe the latest available observations, not real-time or forecast conditions.",
    "Environmental values are NASA POWER grid-cell estimates for the farm's representative point, "
    "not on-farm measurements.",
    "The analysis window applies to the time-series indicators (water, heat); soil and market are "
    "not time-series indicators.",
    "Market value is unavailable: no verified local farm-price source exists for this region.",
)


@dataclass(frozen=True, slots=True)
class EnvironmentSummary:
    """Top-level response envelope for ``/environment/current/``."""

    farm_id: int
    generated_at: datetime
    window_start: date
    window_end: date
    window_days: int
    latest_observation: date | None
    age_days: int | None
    freshness: Freshness
    data_status: IndicatorStatus
    indicators: Mapping[str, IndicatorResult]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "farm_id": self.farm_id,
            "generated_at": self.generated_at.isoformat().replace("+00:00", "Z"),
            "window": {
                "start": self.window_start.isoformat(),
                "end": self.window_end.isoformat(),
                "days": self.window_days,
                "latest_observation": (
                    self.latest_observation.isoformat() if self.latest_observation else None
                ),
                "age_days": self.age_days,
                "freshness": self.freshness.value,
            },
            "data_status": self.data_status.value,
            "freshness": {
                "latest_observation": (
                    self.latest_observation.isoformat() if self.latest_observation else None
                ),
                "age_days": self.age_days,
                "status": self.freshness.value,
            },
            "indicators": {
                code: result.as_dict() for code, result in self.indicators.items()
            },
            "limitations": list(self.limitations),
        }


def build_environment_summary(
    farm: Farm,
    *,
    window_days: int | None = None,
    today: date | None = None,
    now: datetime | None = None,
) -> EnvironmentSummary:
    """Build the four-indicator summary for one farm.

    ``window_days`` is validated by the caller; this function clamps defensively
    so a direct service call can never request an unbounded window.
    """
    days = int(window_days if window_days is not None else default_window_days())
    days = max(1, min(days, max_window_days()))
    today = today or timezone.localdate()
    now = now or timezone.now()

    codes = tuple(RECOMMENDED_PARAMETERS)
    latest = latest_observation_date(farm, codes)

    if latest is not None:
        window_end = latest
        window_start = latest - timedelta(days=days - 1)
        series = window_series(farm, codes, window_start, window_end)
    else:
        # No observations: report the requested window ending today, with no data.
        window_end = today
        window_start = today - timedelta(days=days - 1)
        series = {code: {} for code in codes}

    sources = source_references(codes)
    context = FarmerContext.objects.filter(farm=farm).first()

    water = calculate_water_indicator(
        precipitations=series.get(WATER_PARAMETER, {}),
        start=window_start,
        end=window_end,
        today=today,
        source=sources.get(WATER_PARAMETER),
        irrigation_context=_irrigation_context(context),
    )
    heat = calculate_heat_indicator(
        mean_temperatures=series.get("T2M", {}),
        max_temperatures=series.get("T2M_MAX", {}),
        min_temperatures=series.get("T2M_MIN", {}),
        start=window_start,
        end=window_end,
        today=today,
        sources={code: sources[code] for code in HEAT_PARAMETERS if code in sources},
    )
    soil = calculate_soil_indicator(
        profile=soil_profile_from_context(context),
        today=today,
    )
    market = calculate_market_indicator(
        start=window_start,
        end=window_end,
        today=today,
        region_code=farm.region_code,
        country_code=farm.country_code,
    )

    indicators = {
        "water": water,
        "heat": heat,
        "soil": soil,
        "market": market,
    }

    return EnvironmentSummary(
        farm_id=farm.pk,
        generated_at=now,
        window_start=window_start,
        window_end=window_end,
        window_days=days,
        latest_observation=latest,
        age_days=(today - latest).days if latest else None,
        freshness=freshness_for((today - latest).days if latest else None),
        data_status=overall_data_status(water, heat, soil),
        indicators=indicators,
        limitations=TOP_LEVEL_LIMITATIONS,
    )


def overall_data_status(
    water: IndicatorResult,
    heat: IndicatorResult,
    soil: IndicatorResult,
) -> IndicatorStatus:
    """Top-level status from the assessable indicators.

    ``MARKET`` is excluded on purpose: it is ``UNAVAILABLE`` by design (R18) and
    must not make the whole response look unavailable. Rules:

    * all assessable indicators ``OK`` → ``OK``;
    * at least one ``OK``/``PARTIAL`` → ``PARTIAL``;
    * none assessable → ``INSUFFICIENT_DATA``.
    """
    statuses = {water.status, heat.status, soil.status}
    if statuses == {IndicatorStatus.OK}:
        return IndicatorStatus.OK
    if statuses & {IndicatorStatus.OK, IndicatorStatus.PARTIAL}:
        return IndicatorStatus.PARTIAL
    return IndicatorStatus.INSUFFICIENT_DATA


def _irrigation_context(context: FarmerContext | None) -> tuple[Measurement, ...]:
    """Farmer-reported water context — explanatory only, never scored."""
    if context is None:
        return ()

    items: list[Measurement] = []
    if context.irrigation_available is not None:
        items.append(
            Measurement(
                name="irrigation_available",
                value="yes" if context.irrigation_available else "no",
                unit="boolean",
                quality="FARMER_REPORTED",
                method="farmer-entered",
            )
        )
    if context.irrigation_type:
        items.append(
            Measurement(
                name="irrigation_type",
                value=context.irrigation_type,
                unit="class",
                quality="FARMER_REPORTED",
                method="farmer-entered",
            )
        )
    if context.water_reliability:
        items.append(
            Measurement(
                name="water_reliability",
                value=context.water_reliability,
                unit="class",
                quality="FARMER_REPORTED",
                method="farmer-entered",
            )
        )
    return tuple(items)


__all__ = [
    "EnvironmentSummary",
    "TOP_LEVEL_LIMITATIONS",
    "build_environment_summary",
    "overall_data_status",
]
