"""Source-backed agricultural crop knowledge.

This module deliberately does not reuse ``earth_data.DatasetSource`` or
``EnvironmentalObservation``.  Those models describe NASA-derived environmental
observations for a farm; these models describe research evidence about crops.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class AgriculturalDataset(models.Model):
    """One explicitly approved agricultural research dataset and its version."""

    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed (not importable)"
        APPROVED = "APPROVED", "Approved for import"
        RETIRED = "RETIRED", "Retired"

    identifier = models.CharField(max_length=160)
    title = models.CharField(max_length=300)
    publisher = models.CharField(max_length=200)
    creators = models.JSONField(default=list, blank=True)
    version = models.CharField(max_length=100, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    record_updated_at = models.DateTimeField(null=True, blank=True)
    landing_page_url = models.URLField(max_length=500)
    doi = models.CharField(max_length=255, blank=True)
    license = models.CharField(max_length=300, blank=True)
    license_url = models.URLField(max_length=500, blank=True)
    attribution = models.TextField(blank=True)
    geographic_scope = models.CharField(max_length=300, blank=True)
    temporal_coverage_start = models.DateField(null=True, blank=True)
    temporal_coverage_end = models.DateField(null=True, blank=True)
    spatial_resolution = models.CharField(max_length=160, blank=True)
    temporal_resolution = models.CharField(max_length=120, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROPOSED)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_agricultural_datasets")
    approval_rationale = models.TextField(blank=True)
    approval_evidence_reference = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["identifier", "version"]
        constraints = [
            models.UniqueConstraint(
                fields=["identifier", "version"], name="uniq_ag_dataset_identifier_version"
            ),
            models.CheckConstraint(
                condition=Q(temporal_coverage_end__isnull=True)
                | Q(temporal_coverage_start__isnull=True)
                | Q(temporal_coverage_start__lte=models.F("temporal_coverage_end")),
                name="ag_dataset_temporal_coverage_ordered",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.identifier} ({self.version or 'version unknown'})"


class DatasetResource(models.Model):
    """One verified file or external resource belonging to a dataset release."""

    dataset = models.ForeignKey(
        AgriculturalDataset, on_delete=models.PROTECT, related_name="resources"
    )
    resource_identifier = models.CharField(max_length=255)
    title = models.CharField(max_length=300)
    access_url = models.URLField(max_length=1000)
    file_format = models.CharField(max_length=80, blank=True)
    size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    license = models.CharField(max_length=300, blank=True)
    license_url = models.URLField(max_length=500, blank=True)
    attribution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dataset_id", "resource_identifier"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "resource_identifier"], name="uniq_ag_dataset_resource_id"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.dataset.identifier}:{self.resource_identifier}"


class DatasetImport(models.Model):
    """Auditable, idempotent import attempt; it never stores a local source path."""

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        PARTIAL = "PARTIAL", "Partially succeeded"
        FAILED = "FAILED", "Failed"
        SKIPPED = "SKIPPED", "Already imported"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(AgriculturalDataset, on_delete=models.PROTECT, related_name="imports")
    resource = models.ForeignKey(
        DatasetResource, on_delete=models.PROTECT, null=True, blank=True, related_name="imports"
    )
    source_file_name = models.CharField(max_length=255, blank=True)
    source_checksum = models.CharField(max_length=128)
    resource_key = models.CharField(max_length=32, default="", blank=True)
    mapping_version = models.CharField(max_length=80, default="1")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    total_records = models.PositiveIntegerField(default=0)
    imported_records = models.PositiveIntegerField(default=0)
    skipped_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "resource_key", "source_checksum"],
                condition=Q(status="RUNNING"),
                name="uniq_ag_import_running_attempt",
            ),
        ]


class RegionAgronomyProfile(models.Model):
    """Versioned, approved regional crop calendar configuration."""

    region_code = models.CharField(max_length=80)
    country_code = models.CharField(max_length=2, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    season_cycle_start_month_day = models.CharField(max_length=5, blank=True)
    calendar_version = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=AgriculturalDataset.Status.choices, default=AgriculturalDataset.Status.PROPOSED)
    source_title = models.CharField(max_length=300, blank=True)
    source_publisher = models.CharField(max_length=200, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    evidence_reference = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_agronomy_profiles")
    approval_rationale = models.TextField(blank=True)
    approval_evidence_reference = models.TextField(blank=True)

    class Meta:
        ordering = ["region_code", "calendar_version"]
        constraints = [models.UniqueConstraint(fields=["region_code", "calendar_version"], name="uniq_region_calendar_version")]


class RegionSeason(models.Model):
    """A sourced season slot in a regional rotation calendar."""

    profile = models.ForeignKey(RegionAgronomyProfile, on_delete=models.PROTECT, related_name="seasons")
    season_code = models.CharField(max_length=80)
    label = models.CharField(max_length=120)
    sequence = models.PositiveSmallIntegerField()
    start_month_day = models.CharField(max_length=5)
    end_month_day = models.CharField(max_length=5)
    evidence_reference = models.TextField()
    source_url = models.URLField(max_length=500)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [models.UniqueConstraint(fields=["profile", "season_code"], name="uniq_region_season_code")]


class RegionSeasonCrop(models.Model):
    """A crop/calendar association with source-backed local planting/harvest windows."""

    season = models.ForeignKey(RegionSeason, on_delete=models.PROTECT, related_name="crop_windows")
    crop = models.ForeignKey("agronomy.Crop", on_delete=models.PROTECT, related_name="region_seasons")
    planting_window = models.CharField(max_length=120, blank=True)
    harvest_window = models.CharField(max_length=120, blank=True)
    evidence_reference = models.TextField()
    source_url = models.URLField(max_length=500)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["season", "crop"], name="uniq_season_crop_window")]


class GeographicApplicability(models.TextChoices):
    DIRECT = "DIRECT", "Direct Egypt/Gharbia evidence"
    GENERAL = "GENERAL", "Global or general crop information"
    TRANSFERABLE_LIMITED = "TRANSFERABLE_LIMITED", "Transferable with limitations"
    US_SPECIFIC = "US_SPECIFIC", "U.S.-specific evidence"
    UNKNOWN = "UNKNOWN", "Unknown applicability"


class ReviewRequest(models.Model):
    """Append-only moderation decision for a dataset, calendar, rule, or trait."""

    class TargetType(models.TextChoices):
        DATASET = "DATASET", "Agricultural dataset"
        CALENDAR = "CALENDAR", "Regional calendar"
        ROTATION_RULE = "ROTATION_RULE", "Rotation rule"
        CROP_TRAIT = "CROP_TRAIT", "Crop characteristic"

    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        RETURNED = "RETURNED", "Returned for revision"

    target_type = models.CharField(max_length=20, choices=TargetType.choices)
    target_id = models.PositiveBigIntegerField()
    decision = models.CharField(max_length=16, choices=Decision.choices)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="agronomy_review_decisions")
    rationale = models.TextField()
    evidence_reference = models.TextField()
    geographic_applicability = models.CharField(max_length=24, choices=GeographicApplicability.choices, blank=True)
    applicability_justification = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["target_type", "target_id", "-created_at"], name="ag_review_target_idx")]


class CropRotationRule(models.Model):
    """Explicitly reviewed, evidence-linked rotation constraint."""

    class RuleType(models.TextChoices):
        FORBID_ADJACENT_CROP = "FORBID_ADJACENT_CROP", "Forbid crop in adjacent slots"

    profile = models.ForeignKey(RegionAgronomyProfile, on_delete=models.PROTECT, related_name="rotation_rules")
    identifier = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=40, choices=RuleType.choices)
    crop = models.ForeignKey("agronomy.Crop", on_delete=models.PROTECT, related_name="rotation_rules")
    description = models.TextField()
    source_title = models.CharField(max_length=300)
    source_url = models.URLField(max_length=500)
    evidence_reference = models.TextField()
    approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_rotation_rules")
    approval_rationale = models.TextField(blank=True)
    approval_evidence_reference = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["profile", "identifier"], name="uniq_rotation_rule_identifier")]


class RotationRecommendation(models.Model):
    """Immutable, reproducible assessment snapshot for one farm."""

    class Status(models.TextChoices):
        OPTIONS_AVAILABLE = "OPTIONS_AVAILABLE", "Options available"
        INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE", "Insufficient evidence"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="rotation_recommendations")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="rotation_recommendations"
    )
    engine_version = models.CharField(max_length=40)
    input_snapshot = models.JSONField()
    input_sha256 = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=128, blank=True)
    assessment = models.JSONField()
    status = models.CharField(max_length=32, choices=Status.choices)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at", "-id"]
        indexes = [models.Index(fields=["farm", "-generated_at"], name="rotation_farm_generated_idx")]
        constraints = [models.UniqueConstraint(fields=["farm", "requested_by", "idempotency_key"], condition=~Q(idempotency_key=""), name="uniq_rotation_idempotency_key")]


class CropSourceIdentity(models.Model):
    """A source-specific crop identifier; canonical linkage requires review."""

    source_crop = models.OneToOneField("agronomy.Crop", on_delete=models.PROTECT, related_name="source_identity")
    dataset = models.ForeignKey(AgriculturalDataset, on_delete=models.PROTECT, related_name="crop_identities")
    source_crop_identifier = models.CharField(max_length=160)
    canonical_crop = models.ForeignKey("agronomy.Crop", null=True, blank=True, on_delete=models.PROTECT, related_name="source_identities")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_crop_identities")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_rationale = models.TextField(blank=True)
    evidence_reference = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dataset", "source_crop_identifier"], name="uniq_dataset_source_crop_identity")]


class CropAlias(models.Model):
    """Reviewed farmer-entered name/code crosswalk; ambiguous names are not guessed."""

    region_code = models.CharField(max_length=80)
    alias = models.CharField(max_length=160)
    canonical_crop = models.ForeignKey("agronomy.Crop", on_delete=models.PROTECT, related_name="aliases")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reviewed_crop_aliases")
    reviewed_at = models.DateTimeField(auto_now_add=True)
    rationale = models.TextField()
    evidence_reference = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["region_code", "alias", "canonical_crop"], name="uniq_region_crop_alias_target")]
        indexes = [models.Index(fields=["region_code", "alias", "is_active"], name="crop_alias_lookup_idx")]


class Crop(models.Model):
    """A crop identity; traits, not the identity row, hold source evidence."""

    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    scientific_name = models.CharField(max_length=200, blank=True)
    crop_family = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "code"]

    def __str__(self) -> str:
        return self.name


class ValidationStatus(models.TextChoices):
    VALID = "VALID", "Validated"
    REVIEW_REQUIRED = "REVIEW_REQUIRED", "Requires review"
    REJECTED = "REJECTED", "Rejected"


class CropCharacteristic(models.Model):
    """A single source record's crop characteristic, retaining its original value."""

    class ValueType(models.TextChoices):
        NUMBER = "NUMBER", "Number"
        TEXT = "TEXT", "Text"
        BOOLEAN = "BOOLEAN", "Boolean"

    crop = models.ForeignKey(Crop, on_delete=models.PROTECT, related_name="characteristics")
    dataset = models.ForeignKey(AgriculturalDataset, on_delete=models.PROTECT, related_name="characteristics")
    dataset_import = models.ForeignKey(DatasetImport, on_delete=models.PROTECT, related_name="characteristics")
    # Immutable source snapshot: the dataset registry may later receive a new
    # version, but historical evidence must continue to describe what was used.
    original_dataset_identifier = models.CharField(max_length=160)
    original_dataset_title = models.CharField(max_length=300)
    original_dataset_landing_page_url = models.URLField(max_length=500, blank=True, default="")
    original_publisher = models.CharField(max_length=200)
    source_resource_identifier = models.CharField(max_length=255, blank=True)
    source_resource_url = models.URLField(max_length=1000, blank=True)
    original_dataset_version = models.CharField(max_length=100, blank=True)
    source_doi = models.CharField(max_length=255, blank=True)
    source_license = models.CharField(max_length=300, blank=True)
    source_attribution = models.TextField(blank=True)
    source_crop_identifier = models.CharField(max_length=160)
    cultivar_or_variety = models.CharField(max_length=200, blank=True)
    characteristic_name = models.CharField(max_length=160)
    value_type = models.CharField(max_length=12, choices=ValueType.choices)
    original_value = models.TextField(null=True, blank=True)
    original_unit = models.CharField(max_length=80, blank=True)
    normalized_value = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    normalized_text = models.TextField(null=True, blank=True)
    normalized_boolean = models.BooleanField(null=True, blank=True)
    normalized_unit = models.CharField(max_length=80, blank=True)
    temporal_applicability = models.CharField(max_length=300, blank=True)
    geographic_scope = models.CharField(max_length=300, blank=True)
    geographic_applicability = models.CharField(
        max_length=24, choices=GeographicApplicability.choices, default=GeographicApplicability.UNKNOWN
    )
    source_record_identifier = models.CharField(max_length=255)
    source_record_url = models.URLField(max_length=500, blank=True)
    evidence_reference = models.TextField(blank=True)
    # Source-asserted applicability is retained as a claim, never trusted as an approval.
    source_geographic_applicability_claim = models.CharField(max_length=24, blank=True)
    approval_status = models.CharField(max_length=16, choices=[("PENDING", "Pending review"), ("APPROVED", "Approved for use"), ("REJECTED", "Rejected")], default="PENDING")
    approved_geographic_applicability = models.CharField(max_length=24, choices=GeographicApplicability.choices, default=GeographicApplicability.UNKNOWN)
    applicability_justification = models.TextField(blank=True)
    validation_status = models.CharField(
        max_length=20, choices=ValidationStatus.choices, default=ValidationStatus.REVIEW_REQUIRED
    )
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_crop_characteristics")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_rationale = models.TextField(blank=True)
    review_evidence_reference = models.TextField(blank=True)
    revision = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by")
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["crop_id", "characteristic_name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "source_record_identifier", "characteristic_name", "cultivar_or_variety", "temporal_applicability"],
                condition=Q(is_current=True),
                name="uniq_ag_current_trait_evidence_dimensions",
            ),
            models.CheckConstraint(
                condition=Q(normalized_value__isnull=True) | ~Q(normalized_unit=""),
                name="ag_trait_normalized_value_has_unit",
            ),
            models.CheckConstraint(
                condition=(
                    Q(value_type="NUMBER", normalized_text__isnull=True, normalized_boolean__isnull=True)
                    | Q(value_type="TEXT", normalized_value__isnull=True, normalized_boolean__isnull=True)
                    | Q(value_type="BOOLEAN", normalized_value__isnull=True, normalized_text__isnull=True)
                ),
                name="ag_trait_single_normalized_value_type",
            ),
        ]
        indexes = [
            models.Index(fields=["crop", "characteristic_name"], name="ag_trait_crop_name_idx"),
            models.Index(fields=["dataset", "validation_status"], name="ag_trait_dataset_status_idx"),
        ]


__all__ = [
    "AgriculturalDataset", "Crop", "CropCharacteristic", "DatasetImport",
    "GeographicApplicability", "ValidationStatus",
]
