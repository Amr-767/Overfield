"""Environmental observation storage (Phase 3C).

Design notes
------------
**Structured rows, not JSON blobs.** Each daily value is its own
``EnvironmentalObservation`` row. This keeps the unique
``(farm, source, observation_date)`` constraint enforceable in the database
(so re-imports cannot duplicate), makes time-series queries (date ranges,
per-parameter filters, aggregates, window functions) ordinary SQL, and lets
units/provenance live on a foreign key instead of being re-parsed from JSON.
A JSON column would need application-side de-duplication and would make
Phase 4 indicator queries and Phase 5 rotation analysis much harder.

**Decimal, not float.** POWER publishes two decimals (e.g. ``16.15`` °C);
values are stored as ``Decimal(10, 4)`` so repeated imports and later sums do
not accumulate binary-float drift.

**Provenance.** Observations reference both the farm and the fetch job that
produced them, and keep the requested coordinates (where we asked) separate
from the returned coordinates (where POWER answered, snapped to 0.001° and
reported with an elevation).

The only way to create an observation through the service layer is from a
:class:`apps.earth_data.providers.power.PowerResponse`; client-supplied values
are never accepted as NASA data (ADR-013, Risk R14).
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Provider(models.TextChoices):
    NASA_POWER = "NASA_POWER", "NASA POWER"


class DataCategory(models.TextChoices):
    REANALYSIS_OR_ASSIMILATION_ESTIMATE = (
        "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        "Reanalysis or assimilation estimate",
    )
    SATELLITE_DERIVED_ESTIMATE = "SATELLITE_DERIVED_ESTIMATE", "Satellite-derived estimate"
    DERIVED = "DERIVED", "Derived from provider products"


class DailyAggregation(models.TextChoices):
    MEAN = "MEAN", "Mean of hourly values"
    MAXIMUM = "MAXIMUM", "Daily maximum"
    MINIMUM = "MINIMUM", "Daily minimum"
    TOTAL = "TOTAL", "Daily total"


class TemporalResolution(models.TextChoices):
    DAILY = "DAILY", "Daily"


class TimeStandard(models.TextChoices):
    UTC = "UTC", "Coordinated Universal Time"
    LST = "LST", "Local Solar Time"


class DatasetSource(models.Model):
    """One provider parameter: the catalogue row observations point at.

    Seeded from the verified Phase 3A/3B parameter list. ``units`` is stored
    per row because the API is authoritative for units, not our code.
    """

    provider = models.CharField(
        max_length=32, choices=Provider.choices, default=Provider.NASA_POWER
    )
    product = models.CharField(max_length=64, help_text="e.g. MERRA-2, CERES SYN1deg")
    parameter_code = models.CharField(max_length=32, help_text="Provider parameter code, e.g. T2M")
    long_name = models.CharField(max_length=160)
    units = models.CharField(max_length=32)
    community = models.CharField(max_length=8, default="AG")
    temporal_resolution = models.CharField(
        max_length=16, choices=TemporalResolution.choices, default=TemporalResolution.DAILY
    )
    time_standard = models.CharField(
        max_length=8, choices=TimeStandard.choices, default=TimeStandard.UTC
    )
    data_category = models.CharField(max_length=48, choices=DataCategory.choices)
    daily_aggregation = models.CharField(max_length=16, choices=DailyAggregation.choices)
    native_resolution_note = models.CharField(
        max_length=120,
        blank=True,
        help_text="Documented native grid support, or blank when it has not been verified.",
    )
    first_available_date = models.DateField(
        help_text="First date with published values for this parameter."
    )
    attribution = models.CharField(max_length=200, blank=True)
    docs_url = models.URLField(max_length=300, blank=True)
    access_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the parameter metadata was last verified against the provider.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["parameter_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "parameter_code", "community", "time_standard"],
                name="uniq_source_provider_parameter_community_standard",
            ),
            models.CheckConstraint(
                condition=Q(units__gt=""),
                name="source_units_not_blank",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "is_active"], name="source_provider_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.parameter_code} ({self.units})"


class DataFetchJob(models.Model):
    """History of one attempt to fetch environmental data for one farm."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        PARTIALLY_SUCCEEDED = "PARTIALLY_SUCCEEDED", "Partially succeeded"
        FAILED = "FAILED", "Failed"

    class RequestGeometrySource(models.TextChoices):
        FARMER_LOCATION = "FARMER_LOCATION", "Farmer-registered location point"
        POINT_ON_SURFACE = "POINT_ON_SURFACE", "Point on the farm boundary surface"
        CENTROID = "CENTROID", "Geometry centroid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.CASCADE,
        related_name="data_fetch_jobs",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_fetch_jobs",
    )
    provider = models.CharField(
        max_length=32, choices=Provider.choices, default=Provider.NASA_POWER
    )
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)

    requested_start = models.DateField()
    requested_end = models.DateField()
    parameters = models.JSONField(
        default=list, help_text="Parameter codes exactly as requested from the provider."
    )

    requested_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    requested_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    request_geometry_source = models.CharField(
        max_length=24,
        choices=RequestGeometrySource.choices,
        default=RequestGeometrySource.FARMER_LOCATION,
    )

    returned_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    returned_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    returned_elevation_m = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    api_name = models.CharField(max_length=80, blank=True)
    api_version = models.CharField(max_length=32, blank=True)
    source_products = models.JSONField(
        default=list, help_text="Provider source products reported for this response."
    )
    time_standard = models.CharField(
        max_length=8, choices=TimeStandard.choices, default=TimeStandard.UTC
    )
    fill_value = models.DecimalField(max_digits=8, decimal_places=3, default=-999)

    days_requested = models.PositiveIntegerField(default=0)
    days_stored = models.PositiveIntegerField(default=0)
    days_missing = models.PositiveIntegerField(default=0)

    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(requested_start__lte=F("requested_end")),
                name="fetch_job_range_ordered",
            ),
            models.CheckConstraint(
                condition=Q(requested_latitude__gte=-90) & Q(requested_latitude__lte=90),
                name="fetch_job_latitude_range",
            ),
            models.CheckConstraint(
                condition=Q(requested_longitude__gte=-180) & Q(requested_longitude__lte=180),
                name="fetch_job_longitude_range",
            ),
            # At most one active fetch per farm: a second concurrent scan is
            # rejected by the database instead of hammering the provider.
            models.UniqueConstraint(
                fields=["farm"],
                condition=Q(status="RUNNING"),
                name="uniq_running_job_per_farm",
            ),
        ]
        indexes = [
            models.Index(fields=["farm", "-created_at"], name="job_farm_created_idx"),
            models.Index(fields=["status"], name="job_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.provider} job {self.pk} for farm {self.farm_id} ({self.status})"


class EnvironmentalObservation(models.Model):
    """One provider value for one farm on one day."""

    class QualityStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        MISSING = "MISSING", "Missing / not published"

    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.CASCADE,
        related_name="environmental_observations",
    )
    source = models.ForeignKey(
        DatasetSource,
        # The catalogue must not disappear while observations reference it.
        on_delete=models.PROTECT,
        related_name="observations",
    )
    observation_date = models.DateField()

    value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Provider value; NULL means not published (never imputed).",
    )
    quality_status = models.CharField(
        max_length=16, choices=QualityStatus.choices, default=QualityStatus.AVAILABLE
    )

    fetch_job = models.ForeignKey(
        DataFetchJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observations",
        help_text="Fetch operation that produced (or last refreshed) this value.",
    )
    requested_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    requested_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    returned_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    returned_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["farm_id", "source_id", "observation_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "source", "observation_date"],
                name="uniq_farm_source_observation_date",
            ),
            models.CheckConstraint(
                condition=(
                    Q(quality_status="AVAILABLE", value__isnull=False)
                    | Q(quality_status="MISSING", value__isnull=True)
                ),
                name="observation_value_matches_quality",
            ),
            models.CheckConstraint(
                condition=Q(requested_latitude__gte=-90) & Q(requested_latitude__lte=90),
                name="observation_latitude_range",
            ),
            models.CheckConstraint(
                condition=Q(requested_longitude__gte=-180) & Q(requested_longitude__lte=180),
                name="observation_longitude_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["farm", "observation_date"], name="obs_farm_date_idx"
            ),
            models.Index(
                fields=["source", "observation_date"], name="obs_source_date_idx"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.source.parameter_code} {self.observation_date.isoformat()} "
            f"= {self.value} {self.source.units}"
        )


__all__ = [
    "DataCategory",
    "DailyAggregation",
    "DataFetchJob",
    "DatasetSource",
    "EnvironmentalObservation",
    "Provider",
    "TemporalResolution",
    "TimeStandard",
]
