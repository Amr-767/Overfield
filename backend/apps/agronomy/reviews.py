"""Audited, staff-only approval service for agricultural evidence."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    AgriculturalDataset,
    CropCharacteristic,
    CropRotationRule,
    GeographicApplicability,
    RegionAgronomyProfile,
    ReviewRequest,
    ValidationStatus,
)


def review_evidence(*, reviewer, target_type: str, target_id: int, decision: str,
                    rationale: str, evidence_reference: str,
                    geographic_applicability: str = "",
                    applicability_justification: str = "") -> ReviewRequest:
    """Record a decision; imported source fields cannot substitute for review."""
    if not reviewer or not reviewer.is_authenticated or not reviewer.is_staff:
        raise PermissionDenied("Staff reviewer permission is required.")
    if not rationale.strip() or not evidence_reference.strip():
        raise ValidationError("A review rationale and evidence reference are required.")
    if decision not in ReviewRequest.Decision.values:
        raise ValidationError("Unsupported review decision.")
    if geographic_applicability and geographic_applicability not in GeographicApplicability.values:
        raise ValidationError("Unsupported geographic applicability.")
    if geographic_applicability in {GeographicApplicability.GENERAL, GeographicApplicability.TRANSFERABLE_LIMITED} and not applicability_justification.strip():
        raise ValidationError("Transferability justification is required for general or limited-transfer evidence.")
    if geographic_applicability == GeographicApplicability.DIRECT and not evidence_reference.strip():
        raise ValidationError("Direct regional applicability requires supporting evidence.")

    with transaction.atomic():
        target = _lock_target(target_type, target_id)
        review = ReviewRequest.objects.create(
            target_type=target_type, target_id=target_id, decision=decision,
            reviewer=reviewer, rationale=rationale.strip(),
            evidence_reference=evidence_reference.strip(),
            geographic_applicability=geographic_applicability,
            applicability_justification=applicability_justification.strip(),
        )
        approved = decision == ReviewRequest.Decision.APPROVED
        if target_type == ReviewRequest.TargetType.DATASET:
            target.status = AgriculturalDataset.Status.APPROVED if approved else AgriculturalDataset.Status.RETIRED if decision == ReviewRequest.Decision.REJECTED else AgriculturalDataset.Status.PROPOSED
            target.approved_by = reviewer if approved else None
            target.approved_at = timezone.now() if approved else None
            target.approval_rationale = rationale.strip() if approved else ""
            target.approval_evidence_reference = evidence_reference.strip() if approved else ""
            target.save(update_fields=["status", "approved_by", "approved_at", "approval_rationale", "approval_evidence_reference", "updated_at"])
        elif target_type == ReviewRequest.TargetType.CALENDAR:
            target.status = AgriculturalDataset.Status.APPROVED if approved else AgriculturalDataset.Status.RETIRED if decision == ReviewRequest.Decision.REJECTED else AgriculturalDataset.Status.PROPOSED
            target.approved_by = reviewer if approved else None
            target.approved_at = timezone.now() if approved else None
            target.approval_rationale = rationale.strip() if approved else ""
            target.approval_evidence_reference = evidence_reference.strip() if approved else ""
            target.save(update_fields=["status", "approved_by", "approved_at", "approval_rationale", "approval_evidence_reference"])
        elif target_type == ReviewRequest.TargetType.ROTATION_RULE:
            target.approved = approved
            target.approved_by = reviewer if approved else None
            target.approved_at = timezone.now() if approved else None
            target.approval_rationale = rationale.strip() if approved else ""
            target.approval_evidence_reference = evidence_reference.strip() if approved else ""
            target.save(update_fields=["approved", "approved_by", "approved_at", "approval_rationale", "approval_evidence_reference"])
        elif target_type == ReviewRequest.TargetType.CROP_TRAIT:
            target.approval_status = "APPROVED" if approved else "REJECTED" if decision == ReviewRequest.Decision.REJECTED else "PENDING"
            target.validation_status = ValidationStatus.VALID if approved else ValidationStatus.REJECTED if decision == ReviewRequest.Decision.REJECTED else ValidationStatus.REVIEW_REQUIRED
            target.reviewed_by = reviewer if approved else None
            target.reviewed_at = timezone.now() if approved else None
            target.review_rationale = rationale.strip() if approved else ""
            target.review_evidence_reference = evidence_reference.strip() if approved else ""
            target.approved_geographic_applicability = geographic_applicability if approved else GeographicApplicability.UNKNOWN
            target.geographic_applicability = geographic_applicability if approved else GeographicApplicability.UNKNOWN
            target.applicability_justification = applicability_justification.strip() if approved else ""
            target.save(update_fields=["approval_status", "validation_status", "reviewed_by", "reviewed_at", "review_rationale", "review_evidence_reference", "approved_geographic_applicability", "geographic_applicability", "applicability_justification"])
        return review


def _lock_target(target_type: str, target_id: int):
    model = {
        ReviewRequest.TargetType.DATASET: AgriculturalDataset,
        ReviewRequest.TargetType.CALENDAR: RegionAgronomyProfile,
        ReviewRequest.TargetType.ROTATION_RULE: CropRotationRule,
        ReviewRequest.TargetType.CROP_TRAIT: CropCharacteristic,
    }.get(target_type)
    if model is None:
        raise ValidationError("Unsupported review target type.")
    try:
        return model.objects.select_for_update().get(pk=target_id)
    except model.DoesNotExist as exc:
        raise ValidationError("Review target does not exist.") from exc
