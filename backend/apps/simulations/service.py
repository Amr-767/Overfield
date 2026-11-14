"""Deterministic, environment-only scenario simulation (Phase 6.2/6.3).

What this module does
---------------------
It applies a **user-declared, bounded hypothetical adjustment** to environmental
observations that are already stored for a farm, then reports what the recorded
evidence looks like under that assumption.

What it deliberately does not do
--------------------------------
* It never calls a provider and never invents observations.
* It never projects a future trajectory. The horizon checkpoints reuse the
  stored observation window because no approved regional calendar exists to
  anchor real future dates (``as_of_date`` stays ``NULL``).
* It never simulates crop-level outcomes, yield, profit or soil carbon. The
  production crop catalogue is empty, so a crop-level claim would be fabricated.
* It never produces a 0–100 score, a rank or a "best strategy" claim.

Reproducibility
---------------
The canonical input snapshot is serialised with sorted keys and SHA-256 hashed.
The same inputs and engine version produce the same hash and the same output.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from django.db import transaction
from django.utils import timezone

from apps.farms.models import Farm
from apps.indicators.coverage import (
    count_days,
    default_window_days,
    freshness_for,
    latest_window,
    max_window_days,
)
from apps.indicators.selectors import (
    latest_observation_date,
    observed_dates,
    source_references,
    window_series,
)

from .models import (
    ScenarioMode,
    SimulationRun,
    SimulationStatus,
    SimulationStep,
)

ENGINE_VERSION = "phase6-env-1.0.0"

TEMPERATURE_PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN")
RAINFALL_PARAMETER = "PRECTOTCORR"
SIMULATED_PARAMETERS = TEMPERATURE_PARAMETERS + (RAINFALL_PARAMETER,)

HOT_DAY_THRESHOLD_C = Decimal("35")
VERY_HOT_DAY_THRESHOLD_C = Decimal("40")
COOL_NIGHT_THRESHOLD_C = Decimal("5")
RAINY_DAY_THRESHOLD_MM = Decimal("1.0")

MIN_TEMPERATURE_DELTA_C = Decimal("-5.00")
MAX_TEMPERATURE_DELTA_C = Decimal("5.00")
MIN_RAINFALL_MULTIPLIER = Decimal("0.20")
MAX_RAINFALL_MULTIPLIER = Decimal("2.00")

HYPOTHETICAL_NOTICE = (
    "Scenario adjustments are user-declared hypothetical assumptions applied to stored "
    "NASA POWER observations. They are not a NASA forecast, prediction or measurement."
)

BASE_LIMITATIONS = (
    HYPOTHETICAL_NOTICE,
    "The stored window ends at the latest usable NASA POWER observation, never at today.",
    "NASA POWER values are grid-cell reanalysis estimates, not on-farm measurements.",
    "Horizon checkpoints repeat the stored observation window; no future trajectory is projected.",
    "No crop-level outcome, yield, profit or soil-carbon effect is simulated.",
    "No approved regional crop calendar exists, so crop-level scenario outcomes are not simulated.",
)

CHECKPOINTS: tuple[tuple[str, str, int], ...] = (
    ("PRESENT", "Present — stored observation window", 0),
    ("PLUS_6_MONTHS", "+6 months — repeated-observation horizon", 6),
    ("PLUS_1_YEAR", "+1 year — repeated-observation horizon", 12),
    ("PLUS_2_YEARS", "+2 years — repeated-observation horizon", 24),
)

_PRESET_LABELS = {
    ScenarioMode.BASELINE: "Baseline — stored observations with no adjustment",
    ScenarioMode.HOT_SCENARIO: "Hot scenario — +2.00 °C on stored temperatures",
    ScenarioMode.DRY_SCENARIO: "Dry scenario — stored rainfall × 0.70",
    ScenarioMode.CUSTOM: "Custom — user-declared hypothetical adjustment",
}


class ScenarioValidationError(ValueError):
    """A scenario request that cannot be simulated honestly."""


def _decimal(value: Any, fallback: str) -> Decimal:
    if value is None or value == "":
        return Decimal(fallback)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ScenarioValidationError(f"Cannot interpret {value!r} as a number.") from exc


def _fmt(value: Decimal | None) -> str | None:
    """Render a Decimal as a fixed two-decimal string (never a binary float)."""
    if value is None:
        return None
    return format(value.quantize(Decimal("0.01")), "f")


def _value_str(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def resolve_scenario(
    mode: str,
    *,
    temperature_delta_c: Any = None,
    rainfall_multiplier: Any = None,
) -> dict[str, Any]:
    """Validate and normalise a scenario definition.

    Preset modes are fixed so a stored run always means exactly one thing.
    ``CUSTOM`` requires at least one explicit adjustment.
    """
    mode = (mode or "").strip().upper()
    if mode not in ScenarioMode.values:
        raise ScenarioValidationError(
            f"Unsupported scenario_mode. Allowed values: {', '.join(ScenarioMode.values)}."
        )

    delta = _decimal(temperature_delta_c, "0")
    multiplier = _decimal(rainfall_multiplier, "1")

    if mode == ScenarioMode.BASELINE:
        if delta != 0 or multiplier != 1:
            raise ScenarioValidationError(
                "BASELINE does not accept adjustments; use CUSTOM for a hypothetical change."
            )
        delta, multiplier = Decimal("0"), Decimal("1")
    elif mode == ScenarioMode.HOT_SCENARIO:
        if temperature_delta_c is not None or rainfall_multiplier is not None:
            raise ScenarioValidationError(
                "HOT_SCENARIO uses a fixed +2.00 °C adjustment; use CUSTOM for other values."
            )
        delta, multiplier = Decimal("2.00"), Decimal("1")
    elif mode == ScenarioMode.DRY_SCENARIO:
        if temperature_delta_c is not None or rainfall_multiplier is not None:
            raise ScenarioValidationError(
                "DRY_SCENARIO uses a fixed rainfall multiplier of 0.70; use CUSTOM for other values."
            )
        delta, multiplier = Decimal("0"), Decimal("0.70")
    else:  # CUSTOM
        if temperature_delta_c is None and rainfall_multiplier is None:
            raise ScenarioValidationError(
                "CUSTOM requires temperature_delta_c and/or rainfall_multiplier."
            )

    if not (MIN_TEMPERATURE_DELTA_C <= delta <= MAX_TEMPERATURE_DELTA_C):
        raise ScenarioValidationError(
            f"temperature_delta_c must be between {MIN_TEMPERATURE_DELTA_C} and "
            f"{MAX_TEMPERATURE_DELTA_C} °C."
        )
    if not (MIN_RAINFALL_MULTIPLIER <= multiplier <= MAX_RAINFALL_MULTIPLIER):
        raise ScenarioValidationError(
            f"rainfall_multiplier must be between {MIN_RAINFALL_MULTIPLIER} and "
            f"{MAX_RAINFALL_MULTIPLIER}."
        )

    return {
        "mode": mode,
        "label": _PRESET_LABELS[mode],
        "temperature_delta_c": _fmt(delta),
        "rainfall_multiplier": _fmt(multiplier),
        "is_hypothetical": True,
        "adjustment_basis": "USER_DECLARED_ASSUMPTION",
        "bounds": {
            "temperature_delta_c": [_fmt(MIN_TEMPERATURE_DELTA_C), _fmt(MAX_TEMPERATURE_DELTA_C)],
            "rainfall_multiplier": [_fmt(MIN_RAINFALL_MULTIPLIER), _fmt(MAX_RAINFALL_MULTIPLIER)],
        },
    }


def _apply_adjustment(
    series: Mapping[date, Decimal | None],
    scenario: Mapping[str, Any],
    parameter: str,
) -> dict[date, Decimal | None]:
    """Adjust observed values; ``None`` (missing) stays ``None``."""
    delta = Decimal(str(scenario["temperature_delta_c"]))
    multiplier = Decimal(str(scenario["rainfall_multiplier"]))
    if parameter in TEMPERATURE_PARAMETERS:
        return {day: (None if value is None else value + delta) for day, value in series.items()}
    if parameter == RAINFALL_PARAMETER:
        return {day: (None if value is None else value * multiplier) for day, value in series.items()}
    return dict(series)


def _usable(values: Mapping[date, Decimal | None]) -> list[Decimal]:
    return [value for value in values.values() if value is not None]


def _mean(values: Mapping[date, Decimal | None]) -> Decimal | None:
    usable = _usable(values)
    if not usable:
        return None
    return (sum(usable) / Decimal(len(usable))).quantize(Decimal("0.01"))


def _total(values: Mapping[date, Decimal | None]) -> Decimal | None:
    usable = _usable(values)
    if not usable:
        return None
    return sum(usable).quantize(Decimal("0.01"))


def _count(values: Mapping[date, Decimal | None], predicate) -> int | None:
    usable = _usable(values)
    if not usable:
        return None
    return sum(1 for value in usable if predicate(value))


def compute_metrics(series: Mapping[str, Mapping[date, Decimal | None]]) -> dict[str, Any]:
    """Environment-only metrics for one scenario step (no crop logic, no score)."""
    temperatures = series.get("T2M", {})
    maxima = series.get("T2M_MAX", {})
    minima = series.get("T2M_MIN", {})
    rainfall = series.get(RAINFALL_PARAMETER, {})

    return {
        "mean_temperature_c": _mean(temperatures),
        "mean_max_temperature_c": _mean(maxima),
        "mean_min_temperature_c": _mean(minima),
        "rainfall_total_mm": _total(rainfall),
        "rainy_days": _count(rainfall, lambda value: value >= RAINY_DAY_THRESHOLD_MM),
        "hot_days_max_temperature_ge_35c": _count(maxima, lambda value: value >= HOT_DAY_THRESHOLD_C),
        "very_hot_days_max_temperature_ge_40c": _count(
            maxima, lambda value: value >= VERY_HOT_DAY_THRESHOLD_C
        ),
        "cool_nights_min_temperature_le_5c": _count(
            minima, lambda value: value <= COOL_NIGHT_THRESHOLD_C
        ),
        "days_with_mean_temperature": len(_usable(temperatures)),
        "days_with_rainfall": len(_usable(rainfall)),
    }


def _render_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: (_fmt(value) if isinstance(value, Decimal) else value)
        for key, value in metrics.items()
    }


def _missing_inputs(series: Mapping[str, Mapping[date, Decimal | None]]) -> list[str]:
    missing: list[str] = []
    if not any(_usable(series.get(code, {})) for code in TEMPERATURE_PARAMETERS):
        missing.append("NASA POWER temperature observations (T2M, T2M_MAX, T2M_MIN)")
    else:
        labels = {
            "T2M": "T2M mean temperature",
            "T2M_MAX": "T2M_MAX daily maximum temperature",
            "T2M_MIN": "T2M_MIN daily minimum temperature",
        }
        for code in TEMPERATURE_PARAMETERS:
            if not _usable(series.get(code, {})):
                missing.append(f"NASA POWER {labels[code]} observations")
    if not _usable(series.get(RAINFALL_PARAMETER, {})):
        missing.append("NASA POWER PRECTOTCORR precipitation observations")
    return missing


def _baseline_evidence(farm: Farm, window_days: int) -> dict[str, Any]:
    """Load the stored observation window used as the simulation baseline."""
    latest = latest_observation_date(farm, SIMULATED_PARAMETERS)
    sources = source_references(SIMULATED_PARAMETERS)
    source_payload = [
        {
            "provider": reference.provider,
            "parameter": reference.parameter,
            "units": reference.units,
            "product": reference.product,
            "data_category": reference.data_category,
            "native_resolution_note": reference.native_resolution_note or None,
            "time_standard": reference.time_standard,
            "access_date": reference.access_date.isoformat() if reference.access_date else None,
        }
        for reference in sources.values()
    ]

    if latest is None:
        return {
            "start": None,
            "end": None,
            "latest": None,
            "days_expected": 0,
            "series": {code: {} for code in SIMULATED_PARAMETERS},
            "sources": source_payload,
        }

    dates = observed_dates(farm, SIMULATED_PARAMETERS, end=latest)
    window = latest_window(dates, window_days)
    start, end = window if window is not None else (latest, latest)
    series = window_series(farm, SIMULATED_PARAMETERS, start, end)
    return {
        "start": start,
        "end": end,
        "latest": latest,
        "days_expected": count_days(start, end),
        "series": series,
        "sources": source_payload,
    }


def _parameter_availability(
    series: Mapping[str, Mapping[date, Decimal | None]],
    sources: Mapping[str, Any],
    days_expected: int,
) -> dict[str, Any]:
    availability: dict[str, Any] = {}
    for code in SIMULATED_PARAMETERS:
        available = len(_usable(series.get(code, {})))
        source = sources.get(code)
        availability[code] = {
            "units": getattr(source, "units", "") if source else "",
            "available_days": available,
            "missing_days": max(0, days_expected - available),
        }
    return availability


def _differences(
    baseline: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Absolute differences only; no ranking, weighting or score."""
    result: dict[str, Any] = {}
    for key, base_value in baseline.items():
        scenario_value = scenario.get(key)
        if isinstance(base_value, Decimal) and isinstance(scenario_value, Decimal):
            result[key] = {
                "baseline": _fmt(base_value),
                "scenario": _fmt(scenario_value),
                "change": _fmt(scenario_value - base_value),
            }
        else:
            result[key] = {
                "baseline": _fmt(base_value) if isinstance(base_value, Decimal) else base_value,
                "scenario": (
                    _fmt(scenario_value) if isinstance(scenario_value, Decimal) else scenario_value
                ),
                "change": (
                    scenario_value - base_value
                    if isinstance(base_value, int) and isinstance(scenario_value, int)
                    else None
                ),
            }
    return result


def _step_limitations(
    series: Mapping[str, Mapping[date, Decimal | None]],
    *,
    days_expected: int,
) -> list[str]:
    limitations = list(BASE_LIMITATIONS)
    rainfall_days = len(_usable(series.get(RAINFALL_PARAMETER, {})))
    if rainfall_days and rainfall_days < days_expected:
        limitations.append(
            f"Rainfall total covers {rainfall_days} of {days_expected} days in the window; "
            "missing days are not imputed."
        )
    return limitations


def _build_steps(
    baseline_series: Mapping[str, Mapping[date, Decimal | None]],
    scenario: Mapping[str, Any],
    *,
    start: date | None,
    end: date | None,
    days_expected: int,
    available: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, dict[str, Any]]:
    adjusted = {
        code: _apply_adjustment(baseline_series.get(code, {}), scenario, code)
        for code in SIMULATED_PARAMETERS
    }
    adjusted_metrics = compute_metrics(adjusted)

    steps: list[dict[str, Any]] = []
    for checkpoint, label, horizon in CHECKPOINTS:
        if available:
            steps.append(
                {
                    "checkpoint": checkpoint,
                    "label": label,
                    "horizon_months": horizon,
                    "as_of_date": None,
                    "status": SimulationStatus.COMPLETED.value,
                    "metrics": _render_metrics(adjusted_metrics),
                    "missing_inputs": _missing_inputs(adjusted),
                    "applied_adjustments": {
                        "temperature_delta_c": scenario["temperature_delta_c"],
                        "rainfall_multiplier": scenario["rainfall_multiplier"],
                        "applied_to": list(SIMULATED_PARAMETERS),
                    },
                    "assumptions": [
                        (
                            f"The declared adjustment is applied to stored observations from "
                            f"{start.isoformat()} to {end.isoformat()}."
                            if start and end
                            else "The declared adjustment is applied to the stored observation window."
                        ),
                        (
                            "This checkpoint reuses the stored observation window; it is not a "
                            "future observation or a forecast."
                            if horizon
                            else "No future period is implied by the present checkpoint."
                        ),
                    ],
                    "limitations": _step_limitations(adjusted, days_expected=days_expected),
                }
            )
        else:
            steps.append(
                {
                    "checkpoint": checkpoint,
                    "label": label,
                    "horizon_months": horizon,
                    "as_of_date": None,
                    "status": SimulationStatus.INSUFFICIENT_EVIDENCE.value,
                    "metrics": _render_metrics(compute_metrics({})),
                    "missing_inputs": ["NASA POWER environmental observations for this farm"],
                    "applied_adjustments": {
                        "temperature_delta_c": scenario["temperature_delta_c"],
                        "rainfall_multiplier": scenario["rainfall_multiplier"],
                        "applied_to": [],
                    },
                    "assumptions": [
                        "No stored observation window exists, so no adjustment can be applied.",
                    ],
                    "limitations": [
                        HYPOTHETICAL_NOTICE,
                        "Run a NASA POWER scan for this farm before simulating a scenario.",
                        "No crop-level outcome, yield, profit or soil-carbon effect is simulated.",
                    ],
                }
            )

    baseline_metrics = compute_metrics(baseline_series) if available else None
    differences = (
        _differences(baseline_metrics, adjusted_metrics)
        if baseline_metrics is not None and scenario["mode"] != ScenarioMode.BASELINE
        else {}
    )
    return steps, baseline_metrics, differences


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_simulation(
    farm: Farm,
    *,
    scenario: Mapping[str, Any],
    window_days: int | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Compute the simulation payload without writing anything."""
    days = int(window_days if window_days is not None else default_window_days())
    if days < 1 or days > max_window_days():
        raise ScenarioValidationError(
            f"window_days must be between 1 and {max_window_days()}."
        )
    today = today or timezone.localdate()

    evidence = _baseline_evidence(farm, days)
    series = evidence["series"]
    available = bool(_usable(series.get("T2M_MAX", {})) or _usable(series.get("T2M", {})))

    steps, baseline_metrics, differences = _build_steps(
        series,
        scenario,
        start=evidence["start"],
        end=evidence["end"],
        days_expected=evidence["days_expected"],
        available=available,
    )

    source_map = source_references(SIMULATED_PARAMETERS)
    freshness = freshness_for(
        (today - evidence["latest"]).days if evidence["latest"] else None
    )

    status = (
        SimulationStatus.COMPLETED.value
        if available
        else SimulationStatus.INSUFFICIENT_EVIDENCE.value
    )

    baseline_payload = {
        "period": {
            "start": evidence["start"].isoformat() if evidence["start"] else None,
            "end": evidence["end"].isoformat() if evidence["end"] else None,
            "latest_observation": (
                evidence["latest"].isoformat() if evidence["latest"] else None
            ),
            "days_expected": evidence["days_expected"],
            "freshness": freshness.value,
        },
        "metrics": (
            _render_metrics(baseline_metrics) if baseline_metrics is not None else None
        ),
        "parameters": _parameter_availability(series, source_map, evidence["days_expected"]),
        "sources": evidence["sources"],
        "missing_inputs": _missing_inputs(series) if available else [
            "NASA POWER environmental observations for this farm"
        ],
    }

    snapshot = {
        "engine_version": ENGINE_VERSION,
        "farm_id": farm.pk,
        "window_days": days,
        "scenario": dict(scenario),
        "thresholds": {
            "hot_day_max_temperature_c": _fmt(HOT_DAY_THRESHOLD_C),
            "very_hot_day_max_temperature_c": _fmt(VERY_HOT_DAY_THRESHOLD_C),
            "cool_night_min_temperature_c": _fmt(COOL_NIGHT_THRESHOLD_C),
            "rainy_day_precipitation_mm": _fmt(RAINY_DAY_THRESHOLD_MM),
        },
        "baseline": {
            "start": evidence["start"].isoformat() if evidence["start"] else None,
            "end": evidence["end"].isoformat() if evidence["end"] else None,
            "latest_observation": (
                evidence["latest"].isoformat() if evidence["latest"] else None
            ),
            "series": {
                code: {
                    day.isoformat(): _value_str(value)
                    for day, value in series.get(code, {}).items()
                }
                for code in SIMULATED_PARAMETERS
            },
        },
    }

    limitations = list(BASE_LIMITATIONS)
    if not available:
        limitations.insert(
            1, "No usable stored observations exist, so no scenario value can be computed."
        )
    if available:
        rainfall_days = len(_usable(series.get(RAINFALL_PARAMETER, {})))
        if rainfall_days and rainfall_days < evidence["days_expected"]:
            limitations.append(
                f"Rainfall total covers {rainfall_days} of {evidence['days_expected']} days; "
                "missing days are not imputed."
            )

    return {
        "farm_id": farm.pk,
        "scenario": dict(scenario),
        "engine_version": ENGINE_VERSION,
        "status": status,
        "baseline": baseline_payload,
        "steps": steps,
        "differences": differences,
        "comparison": {
            "supported": status == SimulationStatus.COMPLETED.value,
            "method": (
                "Recorded evidence differences only. No score, rank, winner or "
                "recommendation is produced."
            ),
            "ranked": False,
            "score": None,
        },
        "crop_level_outcomes": "NOT_SIMULATED",
        "hypothetical_notice": HYPOTHETICAL_NOTICE,
        "limitations": limitations,
        "input_snapshot": snapshot,
        "input_sha256": hashlib.sha256(
            _canonical_json(snapshot).encode("utf-8")
        ).hexdigest(),
    }


@transaction.atomic
def create_simulation(
    farm: Farm,
    *,
    requested_by,
    scenario_mode: str,
    temperature_delta_c: Any = None,
    rainfall_multiplier: Any = None,
    window_days: int | None = None,
) -> SimulationRun:
    """Compute and persist one owner-scoped simulation run with its steps."""
    scenario = resolve_scenario(
        scenario_mode,
        temperature_delta_c=temperature_delta_c,
        rainfall_multiplier=rainfall_multiplier,
    )
    payload = build_simulation(farm, scenario=scenario, window_days=window_days)
    snapshot = payload["input_snapshot"]
    evidence = snapshot["baseline"]

    run = SimulationRun.objects.create(
        farm=farm,
        requested_by=requested_by,
        scenario_mode=scenario["mode"],
        temperature_delta_c=Decimal(scenario["temperature_delta_c"]),
        rainfall_multiplier=Decimal(scenario["rainfall_multiplier"]),
        window_days=snapshot["window_days"],
        baseline_start=evidence["start"],
        baseline_end=evidence["end"],
        latest_observation=evidence["latest_observation"],
        engine_version=ENGINE_VERSION,
        status=payload["status"],
        input_snapshot=snapshot,
        input_sha256=payload["input_sha256"],
        result_snapshot={
            "baseline": payload["baseline"],
            "differences": payload["differences"],
            "comparison": payload["comparison"],
            "crop_level_outcomes": payload["crop_level_outcomes"],
            "hypothetical_notice": payload["hypothetical_notice"],
            "limitations": payload["limitations"],
        },
    )
    SimulationStep.objects.bulk_create(
        [
            SimulationStep(
                run=run,
                checkpoint=step["checkpoint"],
                label=step["label"],
                horizon_months=step["horizon_months"],
                as_of_date=step["as_of_date"],
                status=step["status"],
                metrics=step["metrics"],
                missing_inputs=step["missing_inputs"],
                applied_adjustments=step["applied_adjustments"],
                assumptions=step["assumptions"],
                limitations=step["limitations"],
            )
            for step in payload["steps"]
        ]
    )
    return run


def step_payload(step: SimulationStep) -> dict[str, Any]:
    return {
        "checkpoint": step.checkpoint,
        "label": step.label,
        "horizon_months": step.horizon_months,
        "as_of_date": step.as_of_date.isoformat() if step.as_of_date else None,
        "status": step.status,
        "metrics": step.metrics,
        "missing_inputs": step.missing_inputs,
        "applied_adjustments": step.applied_adjustments,
        "assumptions": step.assumptions,
        "limitations": step.limitations,
    }


def simulation_payload(run: SimulationRun) -> dict[str, Any]:
    """Assemble the stored API payload; steps come from their own table."""
    return {
        "simulation_id": str(run.pk),
        "farm_id": run.farm_id,
        "scenario": run.input_snapshot.get("scenario", {}),
        "engine_version": run.engine_version,
        "status": run.status,
        "baseline": run.result_snapshot.get("baseline", {}),
        "differences": run.result_snapshot.get("differences", {}),
        "comparison": run.result_snapshot.get("comparison", {}),
        "crop_level_outcomes": run.result_snapshot.get("crop_level_outcomes", "NOT_SIMULATED"),
        "hypothetical_notice": run.result_snapshot.get("hypothetical_notice", HYPOTHETICAL_NOTICE),
        "limitations": run.result_snapshot.get("limitations", []),
        "steps": [step_payload(step) for step in run.steps.all()],
        "input_sha256": run.input_sha256,
        "created_at": run.created_at.isoformat(),
    }


def steps_payload(run: SimulationRun) -> dict[str, Any]:
    return {
        "simulation_id": str(run.pk),
        "engine_version": run.engine_version,
        "steps": [step_payload(step) for step in run.steps.all()],
        "hypothetical_notice": HYPOTHETICAL_NOTICE,
        "crop_level_outcomes": "NOT_SIMULATED",
    }


__all__ = [
    "BASE_LIMITATIONS",
    "CHECKPOINTS",
    "ENGINE_VERSION",
    "HYPOTHETICAL_NOTICE",
    "RAINFALL_PARAMETER",
    "ScenarioValidationError",
    "SIMULATED_PARAMETERS",
    "TEMPERATURE_PARAMETERS",
    "build_simulation",
    "compute_metrics",
    "create_simulation",
    "resolve_scenario",
    "simulation_payload",
    "step_payload",
    "steps_payload",
]
