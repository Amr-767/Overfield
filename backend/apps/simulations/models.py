"""Scenario simulation persistence (Phase 6.3).

A :class:`SimulationRun` stores one reproducible, *hypothetical* adjustment
applied to environmental observations that are **already stored** for a farm.
It is not a forecast store: every step is derived from observed history and
every response labels the adjustment as a user-declared assumption.

Design notes
------------
* **Snapshot, not recomputation.** The input snapshot and its SHA-256 are
  stored so a run can be explained and reproduced later even after new
  observations arrive.
* **Honest missingness.** JSON snapshots keep ``null`` for unavailable values;
  nothing is imputed.
* **No scores.** There is no score, rank, yield or profit column anywhere.
* **Additive only.** These tables reference Phase 2/3 models but do not modify
  them.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ScenarioMode(models.TextChoices):
    BASELINE = "BASELINE", "Baseline (no adjustment)"
    HOT_SCENARIO = "HOT_SCENARIO", "Hot scenario"
    DRY_SCENARIO = "DRY_SCENARIO", "Dry scenario"
    CUSTOM = "CUSTOM", "Custom scenario"


class SimulationStatus(models.TextChoices):
    COMPLETED = "COMPLETED", "Completed from stored observations"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE", "Insufficient environmental evidence"


class SimulationRun(models.Model):
    """One stored, owner-scoped scenario evaluation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.CASCADE,
        related_name="simulation_runs",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="simulation_runs",
    )

    scenario_mode = models.CharField(max_length=32, choices=ScenarioMode.choices)
    temperature_delta_c = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rainfall_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1)

    window_days = models.PositiveIntegerField(default=30)
    baseline_start = models.DateField(null=True, blank=True)
    baseline_end = models.DateField(null=True, blank=True)
    latest_observation = models.DateField(null=True, blank=True)

    engine_version = models.CharField(max_length=32)
    status = models.CharField(
        max_length=32, choices=SimulationStatus.choices, default=SimulationStatus.COMPLETED
    )

    input_snapshot = models.JSONField(
        help_text="Canonical input evidence; the SHA-256 is computed from this."
    )
    input_sha256 = models.CharField(max_length=64)
    result_snapshot = models.JSONField(
        default=dict,
        help_text="Stored non-step output (baseline, differences, notices, limitations).",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(temperature_delta_c__gte=-5) & Q(temperature_delta_c__lte=5),
                name="simulation_temperature_delta_bounded",
            ),
            models.CheckConstraint(
                condition=Q(rainfall_multiplier__gte=0.2) & Q(rainfall_multiplier__lte=2),
                name="simulation_rainfall_multiplier_bounded",
            ),
            models.CheckConstraint(
                condition=Q(window_days__gte=1) & Q(window_days__lte=366),
                name="simulation_window_days_bounded",
            ),
            models.CheckConstraint(
                condition=Q(input_sha256__regex=r"^[0-9a-f]{64}$"),
                name="simulation_input_sha256_hex",
            ),
            models.CheckConstraint(
                condition=Q(baseline_start__isnull=True)
                | Q(baseline_end__isnull=True)
                | Q(baseline_start__lte=models.F("baseline_end")),
                name="simulation_baseline_range_ordered",
            ),
        ]
        indexes = [
            models.Index(fields=["farm", "-created_at"], name="simulation_farm_created_idx"),
            models.Index(fields=["scenario_mode"], name="simulation_mode_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.scenario_mode} simulation {self.pk} for farm {self.farm_id}"


class SimulationStep(models.Model):
    """One horizon checkpoint of a simulation run.

    Checkpoints beyond ``PRESENT`` reuse the stored observation window; they are
    not future observations. ``as_of_date`` stays ``NULL`` until an approved
    regional calendar exists to anchor a real date.
    """

    run = models.ForeignKey(
        SimulationRun,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    checkpoint = models.CharField(max_length=32)
    label = models.CharField(max_length=160)
    horizon_months = models.PositiveSmallIntegerField(default=0)
    as_of_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=32, choices=SimulationStatus.choices)
    metrics = models.JSONField(default=dict)
    missing_inputs = models.JSONField(default=list)
    applied_adjustments = models.JSONField(default=dict)
    assumptions = models.JSONField(default=list)
    limitations = models.JSONField(default=list)

    class Meta:
        ordering = ["horizon_months", "checkpoint"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "checkpoint"],
                name="uniq_simulation_step_checkpoint",
            ),
            models.CheckConstraint(
                condition=Q(horizon_months__gte=0) & Q(horizon_months__lte=24),
                name="simulation_step_horizon_bounded",
            ),
        ]
        indexes = [
            models.Index(fields=["run", "horizon_months"], name="step_run_horizon_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.run_id}:{self.checkpoint}"


__all__ = [
    "ScenarioMode",
    "SimulationRun",
    "SimulationStatus",
    "SimulationStep",
]
