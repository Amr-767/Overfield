"""Farm, farm zone, farmer context and crop-history models (Phase 2C/2D).

Geometry storage: ``MultiPolygonField(srid=4326)``. SRID 4326 is WGS 84
longitude/latitude; API interchange is GeoJSON with ``[longitude, latitude]``
ordering (ADR-010). Area is always derived on the backend. GeoDjango creates a
GiST spatial index for every geometry field.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models


class Farm(models.Model):
    """A farmer's farm boundary, location and backend-calculated area."""

    class AreaSource(models.TextChoices):
        GEOMETRY_DERIVED = "GEOMETRY_DERIVED", "Derived from boundary geometry (geodesic)"
        FARMER_REPORTED = "FARMER_REPORTED", "Farmer-reported area (lower spatial precision)"

    class GeometrySource(models.TextChoices):
        BOUNDARY = "BOUNDARY", "Drawn or imported polygon boundary"
        LOCATION_POINT = "LOCATION_POINT", "Single location point (no boundary)"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farms",
    )
    name = models.CharField(max_length=120)
    country_code = models.CharField(max_length=2, blank=True)
    region_code = models.CharField(
        max_length=80,
        blank=True,
        help_text="Stable region slug used to select a regional agronomy profile.",
    )
    boundary = gis_models.MultiPolygonField(srid=4326, null=True, blank=True)
    location = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Map marker: the centroid of the boundary, or a tapped point.",
    )
    area_hectares = models.DecimalField(max_digits=14, decimal_places=4)
    area_source = models.CharField(
        max_length=32,
        choices=AreaSource.choices,
        default=AreaSource.GEOMETRY_DERIVED,
    )
    geometry_source = models.CharField(
        max_length=32,
        choices=GeometrySource.choices,
        default=GeometrySource.BOUNDARY,
    )
    timezone = models.CharField(max_length=64, default="UTC")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(boundary__isnull=False) | models.Q(location__isnull=False),
                name="farm_has_boundary_or_location",
            ),
            models.CheckConstraint(
                condition=models.Q(area_hectares__gt=0),
                name="farm_area_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="farm_owner_created_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def spatial_precision(self) -> str:
        """``HIGH`` for a drawn boundary, ``LOW`` for a point-only fallback."""
        if self.geometry_source == self.GeometrySource.BOUNDARY:
            return "HIGH"
        return "LOW"


class FarmZone(models.Model):
    """A sub-area of a farm with distinct crop, soil, irrigation or management.

    Zones are optional and farmer-confirmed; farms are never split automatically.
    """

    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=80)
    boundary = gis_models.MultiPolygonField(srid=4326)
    area_hectares = models.DecimalField(max_digits=14, decimal_places=4)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(area_hectares__gt=0),
                name="farm_zone_area_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.farm.name} / {self.name}"


class FarmerContext(models.Model):
    """Minimum practical farmer inputs for one farm; unknown values stay null."""

    class Provenance(models.TextChoices):
        FARMER_REPORTED = "FARMER_REPORTED", "Farmer-entered"
        LAB_TEST = "LAB_TEST", "Laboratory-tested"
        EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER", "External provider"
        REMOTE_SENSING = "REMOTE_SENSING", "Remote-sensing estimate"
        UNKNOWN = "UNKNOWN", "Unknown"

    class TextureClass(models.TextChoices):
        SAND = "sand", "Sand"
        LOAMY_SAND = "loamy_sand", "Loamy sand"
        SANDY_LOAM = "sandy_loam", "Sandy loam"
        LOAM = "loam", "Loam"
        SILT_LOAM = "silt_loam", "Silt loam"
        SILT = "silt", "Silt"
        CLAY_LOAM = "clay_loam", "Clay loam"
        SANDY_CLAY_LOAM = "sandy_clay_loam", "Sandy clay loam"
        SILTY_CLAY_LOAM = "silty_clay_loam", "Silty clay loam"
        CLAY = "clay", "Clay"
        SANDY_CLAY = "sandy_clay", "Sandy clay"
        SILTY_CLAY = "silty_clay", "Silty clay"
        UNKNOWN = "unknown", "Unknown"

    class IrrigationType(models.TextChoices):
        NONE = "none", "None (rain-fed)"
        SURFACE_CANAL = "surface_canal", "Surface canal"
        DRIP = "drip", "Drip"
        SPRINKLER = "sprinkler", "Sprinkler"
        FLOOD = "flood", "Flood"
        MIXED = "mixed", "Mixed"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"

    class WaterReliability(models.TextChoices):
        RELIABLE = "reliable", "Reliable"
        SEASONAL_VARIABLE = "seasonal_variable", "Seasonally variable"
        UNRELIABLE = "unreliable", "Unreliable"
        UNKNOWN = "unknown", "Unknown"

    farm = models.OneToOneField(Farm, on_delete=models.CASCADE, related_name="context")

    # --- Soil -------------------------------------------------------------
    soil_source = models.CharField(
        max_length=32, choices=Provenance.choices, default=Provenance.FARMER_REPORTED
    )
    texture_class = models.CharField(
        max_length=24, choices=TextureClass.choices, blank=True, default=""
    )
    ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    organic_carbon_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nitrogen_ppm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    phosphorus_ppm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    potassium_ppm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    sampling_depth_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    sampling_method = models.CharField(max_length=120, blank=True)
    lab_name = models.CharField(max_length=120, blank=True)
    sample_date = models.DateField(null=True, blank=True)

    # --- Water ------------------------------------------------------------
    water_source = models.CharField(
        max_length=32, choices=Provenance.choices, default=Provenance.FARMER_REPORTED
    )
    irrigation_available = models.BooleanField(null=True, blank=True)
    irrigation_type = models.CharField(
        max_length=24, choices=IrrigationType.choices, blank=True, default=""
    )
    water_reliability = models.CharField(
        max_length=24, choices=WaterReliability.choices, blank=True, default=""
    )

    # --- Preferences ------------------------------------------------------
    priorities = models.JSONField(
        default=dict,
        blank=True,
        help_text="Named non-negative weights that sum to 1 when supplied.",
    )
    constraints = models.JSONField(
        default=dict,
        blank=True,
        help_text="Explicit practical constraints; null means unknown, not 'none'.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Context for {self.farm.name}"


class FarmCropHistory(models.Model):
    """Ordered season/crop history used as the farmer's current rotation baseline."""

    context = models.ForeignKey(
        FarmerContext,
        on_delete=models.CASCADE,
        related_name="crops",
    )
    season_label = models.CharField(max_length=80)
    crop_name = models.CharField(max_length=120)
    crop_code = models.CharField(
        max_length=64,
        blank=True,
        help_text="Optional catalog code; free-text crop names are allowed before Phase 5.",
    )
    source = models.CharField(
        max_length=32,
        choices=FarmerContext.Provenance.choices,
        default=FarmerContext.Provenance.FARMER_REPORTED,
    )
    notes = models.CharField(max_length=255, blank=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "id"]

    def __str__(self) -> str:
        return f"{self.season_label}: {self.crop_name}"
