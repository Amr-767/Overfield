"""Scenario simulation request serialisers (Phase 6.3)."""

from __future__ import annotations

from rest_framework import serializers

from apps.indicators.coverage import default_window_days, max_window_days

from .models import ScenarioMode
from .service import (
    MAX_RAINFALL_MULTIPLIER,
    MAX_TEMPERATURE_DELTA_C,
    MIN_RAINFALL_MULTIPLIER,
    MIN_TEMPERATURE_DELTA_C,
    ScenarioValidationError,
    resolve_scenario,
)

# Crop-level / strategy-level requests need an approved regional calendar and
# catalogue. Neither exists in production, so the API refuses rather than
# inventing an outcome.
UNSUPPORTED_CROP_KEYS = (
    "planning_seasons",
    "crop_codes",
    "crop_sequence",
    "strategy",
    "include_crop_outcomes",
    "recommended_crops",
)


class CreateSimulationSerializer(serializers.Serializer):
    scenario_mode = serializers.ChoiceField(
        choices=ScenarioMode.choices,
        default=ScenarioMode.BASELINE,
        help_text="BASELINE, HOT_SCENARIO, DRY_SCENARIO or CUSTOM.",
    )
    window_days = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Stored observation window in days (1–366, default 30).",
    )
    temperature_delta_c = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=MIN_TEMPERATURE_DELTA_C,
        max_value=MAX_TEMPERATURE_DELTA_C,
        help_text="CUSTOM only: hypothetical temperature shift applied to stored values.",
    )
    rainfall_multiplier = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        min_value=MIN_RAINFALL_MULTIPLIER,
        max_value=MAX_RAINFALL_MULTIPLIER,
        help_text="CUSTOM only: hypothetical multiplier applied to stored rainfall values.",
    )

    def validate_window_days(self, value: int | None) -> int:
        if value is None:
            return default_window_days()
        limit = max_window_days()
        if value > limit:
            raise serializers.ValidationError(f"window_days must be between 1 and {limit}.")
        return value

    def validate(self, attrs: dict) -> dict:
        unsupported = sorted(key for key in UNSUPPORTED_CROP_KEYS if key in self.initial_data)
        if unsupported:
            raise serializers.ValidationError(
                {
                    key: (
                        "Crop-level simulation requires an approved regional crop catalogue "
                        "and calendar. Neither exists, so this request is refused."
                    )
                    for key in unsupported
                }
            )

        try:
            scenario = resolve_scenario(
                attrs.get("scenario_mode", ScenarioMode.BASELINE),
                temperature_delta_c=attrs.get("temperature_delta_c"),
                rainfall_multiplier=attrs.get("rainfall_multiplier"),
            )
        except ScenarioValidationError as exc:
            raise serializers.ValidationError({"scenario_mode": [str(exc)]}) from exc

        attrs["resolved_scenario"] = scenario
        attrs["window_days"] = attrs.get("window_days", default_window_days())
        return attrs


class SimulationQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=50, default=10)


__all__ = ["CreateSimulationSerializer", "SimulationQuerySerializer", "UNSUPPORTED_CROP_KEYS"]
