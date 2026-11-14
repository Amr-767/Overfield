"""Read-only admin view for stored simulation runs (debugging aid)."""

from django.contrib import admin

from .models import SimulationRun, SimulationStep


class SimulationStepInline(admin.TabularInline):
    model = SimulationStep
    extra = 0
    can_delete = False
    readonly_fields = (
        "checkpoint",
        "label",
        "horizon_months",
        "as_of_date",
        "status",
        "metrics",
        "missing_inputs",
        "applied_adjustments",
        "assumptions",
        "limitations",
    )


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "farm",
        "scenario_mode",
        "status",
        "engine_version",
        "created_at",
    )
    list_filter = ("scenario_mode", "status")
    readonly_fields = (
        "id",
        "farm",
        "requested_by",
        "scenario_mode",
        "temperature_delta_c",
        "rainfall_multiplier",
        "window_days",
        "baseline_start",
        "baseline_end",
        "latest_observation",
        "engine_version",
        "status",
        "input_snapshot",
        "input_sha256",
        "result_snapshot",
        "created_at",
    )
    inlines = [SimulationStepInline]
