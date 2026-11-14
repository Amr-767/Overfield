"""Explicit-schema ingestion for approved agricultural datasets.

The importer intentionally has no generic web scraper.  A dataset is admitted
only after its documented download format has been inspected and a mapping is
provided by the caller.  Tests use fixture rows shaped like a real tabular
source, but production callers must supply the approved dataset's mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    AgriculturalDataset,
    Crop,
    CropCharacteristic,
    DatasetImport,
    DatasetResource,
    GeographicApplicability,
    ValidationStatus,
)


class DatasetValidationError(ValueError):
    """A source row does not satisfy its explicitly approved mapping."""


@dataclass(frozen=True)
class ImportMapping:
    """Names in one verified source file; no presumed Ag Data Commons schema."""

    source_crop_identifier: str
    crop_name: str
    characteristic_name: str
    value: str
    value_type: str
    source_record_identifier: str
    original_unit: str | None = None
    normalized_unit: str | None = None
    scientific_name: str | None = None
    crop_family: str | None = None
    cultivar_or_variety: str | None = None
    geographic_scope: str | None = None
    geographic_applicability: str | None = None
    temporal_applicability: str | None = None
    source_record_url: str | None = None
    evidence_reference: str | None = None
    validation_status: str | None = None
    # Unit semantics are dataset-specific.  Populate this only from the
    # approved dataset documentation; leaving it None intentionally does not
    # pretend a cross-dataset unit vocabulary exists.
    allowed_normalized_units: frozenset[str] | None = None
    # A non-identity conversion must be explicit, reviewed, and source-specific.
    conversion_factor: Decimal | None = None
    mapping_version: str = "1"

    def required_fields(self) -> set[str]:
        return {
            self.source_crop_identifier, self.crop_name, self.characteristic_name,
            self.value, self.value_type, self.source_record_identifier,
        }


def fingerprint_rows(rows: Iterable[Mapping[str, Any]]) -> str:
    """Stable checksum used to make exactly the same file import idempotent."""
    import json

    canonical = json.dumps(list(rows), sort_keys=True, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()


def _field(row: Mapping[str, Any], name: str | None, *, required: bool = False) -> str:
    if not name:
        return ""
    value = row.get(name)
    if value is None:
        if required:
            raise DatasetValidationError(f"missing required field '{name}'")
        return ""
    return str(value).strip()


def _choice(value: str, choices: type, label: str) -> str:
    if value not in choices.values:
        raise DatasetValidationError(f"invalid {label} '{value}'")
    return value


def _normalize_value(
    *, value: str, value_type: str, original_unit: str, normalized_unit: str,
    conversion_factor: Decimal | None,
) -> tuple[Decimal | None, str | None, bool | None]:
    if not value:
        return None, None, None
    if value_type == CropCharacteristic.ValueType.NUMBER:
        if not original_unit or not normalized_unit:
            raise DatasetValidationError("numeric characteristic requires original and normalized units")
        if original_unit != normalized_unit and conversion_factor is None:
            raise DatasetValidationError("unit conversion requires an explicit source-specific conversion factor")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise DatasetValidationError(f"numeric value is invalid: {value!r}") from exc
        normalized = number if conversion_factor is None else number * conversion_factor
        return normalized, None, None
    if value_type == CropCharacteristic.ValueType.BOOLEAN:
        if original_unit or normalized_unit:
            raise DatasetValidationError("boolean characteristic cannot declare numeric units")
        boolean_values = {"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False}
        normalized_boolean = boolean_values.get(value.casefold())
        if normalized_boolean is None:
            raise DatasetValidationError(f"boolean value is invalid: {value!r}")
        return None, None, normalized_boolean
    if original_unit or normalized_unit:
        raise DatasetValidationError("text characteristic cannot declare numeric units")
    return None, value, None


def import_rows(
    *, dataset: AgriculturalDataset, rows: Iterable[Mapping[str, Any]], mapping: ImportMapping,
    resource: DatasetResource | None = None, source_file_name: str = "",
    checksum: str | None = None,
) -> DatasetImport:
    """Validate and import source rows atomically, retaining all original values.

    A previously completed matching checksum returns a ``SKIPPED`` audit row
    only when a separate new attempt can be created.  The unique checksum is
    the idempotency key: callers receive the completed prior import instead of
    duplicate crop traits.
    """
    row_list = list(rows)
    if dataset.status != AgriculturalDataset.Status.APPROVED:
        raise DatasetValidationError("dataset is not approved for import")
    if resource is not None and resource.dataset_id != dataset.pk:
        raise DatasetValidationError("resource does not belong to the selected dataset")
    checksum = checksum or fingerprint_rows(row_list)
    resource_key = str(resource.pk) if resource else ""
    with transaction.atomic():
        existing_query = DatasetImport.objects.select_for_update().filter(
            dataset=dataset, resource_key=resource_key, source_checksum=checksum,
        )
        successful = existing_query.filter(
            mapping_version=mapping.mapping_version,
            status=DatasetImport.Status.SUCCEEDED,
        ).first()
        if successful:
            return successful
        try:
            running = existing_query.filter(status=DatasetImport.Status.RUNNING).first()
            if running:
                return running
            audit = DatasetImport.objects.create(
                dataset=dataset, resource=resource, resource_key=resource_key,
                source_file_name=Path(source_file_name).name, source_checksum=checksum,
                mapping_version=mapping.mapping_version, total_records=len(row_list),
            )
        except IntegrityError:
            running = existing_query.filter(status=DatasetImport.Status.RUNNING).first()
            if running:
                return running
            # An older failed/partial attempt must not poison retries. Keep its
            # row for audit and vary the attempt mapping key deterministically.
            attempt = existing_query.count() + 1
            retry_mapping_version = f"{mapping.mapping_version}:retry:{attempt}"
            audit = DatasetImport.objects.create(
                dataset=dataset, resource=resource, resource_key=resource_key,
                source_file_name=Path(source_file_name).name, source_checksum=checksum,
                mapping_version=retry_mapping_version, total_records=len(row_list),
            )

    errors: list[dict[str, Any]] = []
    imported = skipped = failed = 0
    try:
        with transaction.atomic():
            audit = DatasetImport.objects.select_for_update().get(pk=audit.pk)
            for index, row in enumerate(row_list, start=1):
                unknown = mapping.required_fields() - set(row)
                if unknown:
                    raise DatasetValidationError("source file lacks required fields: " + ", ".join(sorted(unknown)))
                try:
                    source_crop_id = _field(row, mapping.source_crop_identifier, required=True)
                    crop_name = _field(row, mapping.crop_name, required=True)
                    name = _field(row, mapping.characteristic_name, required=True)
                    original_value = _field(row, mapping.value)
                    value_type = _choice(_field(row, mapping.value_type, required=True), CropCharacteristic.ValueType, "value_type")
                    source_record_id = _field(row, mapping.source_record_identifier, required=True)
                    original_unit = _field(row, mapping.original_unit)
                    normalized_unit = _field(row, mapping.normalized_unit) or original_unit
                    normalized_value, normalized_text, normalized_boolean = _normalize_value(
                        value=original_value,
                        value_type=value_type,
                        original_unit=original_unit,
                        normalized_unit=normalized_unit,
                        conversion_factor=mapping.conversion_factor,
                    )
                    if (
                        normalized_value is not None
                        and mapping.allowed_normalized_units is not None
                        and normalized_unit not in mapping.allowed_normalized_units
                    ):
                        raise DatasetValidationError(
                            f"unit '{normalized_unit}' is not approved for this source field"
                        )
                    # These are the source's own claims. They are recorded on the
                    # effective fields so the evidence is usable, while the review
                    # decision stays separate in ``approval_status`` and
                    # ``approved_geographic_applicability`` (never inferred here).
                    geo_claim = _field(row, mapping.geographic_applicability)
                    if geo_claim and geo_claim not in GeographicApplicability.values:
                        raise DatasetValidationError(f"invalid source geographic applicability claim '{geo_claim}'")
                    validation_claim = _field(row, mapping.validation_status)
                    if validation_claim and validation_claim not in ValidationStatus.values:
                        raise DatasetValidationError(f"invalid source validation claim '{validation_claim}'")
                    existing_trait = CropCharacteristic.objects.filter(
                        dataset=dataset,
                        source_record_identifier=source_record_id,
                        characteristic_name=name,
                        cultivar_or_variety=_field(row, mapping.cultivar_or_variety),
                        temporal_applicability=_field(row, mapping.temporal_applicability),
                        is_current=True,
                    ).first()
                    if existing_trait:
                        same_value = (
                            existing_trait.original_value == (original_value or None)
                            and existing_trait.original_unit == original_unit
                            and existing_trait.value_type == value_type
                        )
                        if same_value:
                            skipped += 1
                            continue
                        existing_trait.is_current = False
                        existing_trait.save(update_fields=["is_current"])
                        revision = existing_trait.revision + 1
                    else:
                        revision = 1
                    # Keep dataset identities distinct until an authorized reviewer
                    # establishes a canonical cross-source mapping.
                    crop_code = f"{dataset.identifier}:{source_crop_id}".lower()[:80]
                    crop, _ = Crop.objects.get_or_create(
                        code=crop_code,
                        defaults={
                            "name": crop_name,
                            "scientific_name": _field(row, mapping.scientific_name),
                            "crop_family": _field(row, mapping.crop_family),
                        },
                    )
                    CropCharacteristic.objects.create(
                        dataset=dataset, source_record_identifier=source_record_id,
                        characteristic_name=name,
                        **{
                            "crop": crop, "dataset_import": audit,
                            "original_dataset_identifier": dataset.identifier,
                            "original_dataset_title": dataset.title,
                            "original_dataset_landing_page_url": dataset.landing_page_url,
                            "original_publisher": dataset.publisher,
                            "original_dataset_version": dataset.version,
                            "source_doi": dataset.doi,
                            "source_license": dataset.license,
                            "source_attribution": dataset.attribution,
                            "source_resource_identifier": resource.resource_identifier if resource else "",
                            "source_resource_url": resource.access_url if resource else "",
                            "source_crop_identifier": source_crop_id,
                            "cultivar_or_variety": _field(row, mapping.cultivar_or_variety),
                            "value_type": value_type, "original_value": original_value or None,
                            "original_unit": original_unit, "normalized_value": normalized_value,
                            "normalized_text": normalized_text, "normalized_boolean": normalized_boolean,
                            "normalized_unit": normalized_unit,
                            "temporal_applicability": _field(row, mapping.temporal_applicability),
                            "geographic_scope": _field(row, mapping.geographic_scope),
                            "geographic_applicability": geo_claim or GeographicApplicability.UNKNOWN,
                            "source_geographic_applicability_claim": geo_claim,
                            "source_record_url": _field(row, mapping.source_record_url),
                            "evidence_reference": _field(row, mapping.evidence_reference),
                            "validation_status": validation_claim or ValidationStatus.REVIEW_REQUIRED,
                            "revision": revision,
                            "supersedes": existing_trait,
                            "approval_status": "PENDING",
                            "approved_geographic_applicability": GeographicApplicability.UNKNOWN,
                        },
                    )
                    imported += 1
                except DatasetValidationError as exc:
                    failed += 1
                    errors.append({"row": index, "message": str(exc)})
            audit.imported_records = imported
            audit.skipped_records = skipped
            audit.failed_records = failed
            audit.errors = errors
            audit.status = DatasetImport.Status.PARTIAL if failed else DatasetImport.Status.SUCCEEDED
            audit.finished_at = timezone.now()
            audit.save(update_fields=["imported_records", "skipped_records", "failed_records", "errors", "status", "finished_at"])
    except Exception as exc:
        # The row transaction has rolled back at this point. Audit counts must
        # describe committed state rather than local loop counters.
        audit.imported_records = 0
        audit.skipped_records = 0
        audit.failed_records = len(row_list)
        audit.status = DatasetImport.Status.FAILED
        audit.errors = [{"message": str(exc)}]
        audit.finished_at = timezone.now()
        audit.save(update_fields=["imported_records", "skipped_records", "failed_records", "status", "errors", "finished_at"])
    return audit
