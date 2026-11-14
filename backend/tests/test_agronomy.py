"""Phase 5.1/5.2 tests. Fixture rows are test data, not production crop facts."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.agronomy.imports import DatasetValidationError, ImportMapping, import_rows
from apps.agronomy.models import (
    AgriculturalDataset,
    Crop,
    CropCharacteristic,
    DatasetImport,
    DatasetResource,
    ReviewRequest,
)
from apps.agronomy.reviews import review_evidence

User = get_user_model()


MAPPING = ImportMapping(
    source_crop_identifier="crop_id", crop_name="crop_name", scientific_name="scientific_name",
    crop_family="family", characteristic_name="trait", value="value", value_type="value_type",
    original_unit="unit", normalized_unit="normalized_unit", source_record_identifier="record_id",
    cultivar_or_variety="variety", geographic_scope="geography", geographic_applicability="applicability",
    temporal_applicability="period", source_record_url="record_url", evidence_reference="evidence",
    validation_status="validation",
    allowed_normalized_units=frozenset({"cm"}),
)


def fixture_row(**changes):
    """Deliberately synthetic fixture following the mapped tabular structure."""
    row = {
        "crop_id": "TRITICUM_TEST", "crop_name": "Test wheat", "scientific_name": "Triticum testum",
        "family": "Poaceae", "trait": "root_depth", "value": "120", "value_type": "NUMBER",
        "unit": "cm", "normalized_unit": "cm", "record_id": "fixture-record-1", "variety": "",
        "geography": "United States test plots", "applicability": "US_SPECIFIC", "period": "2019 season",
        "record_url": "https://example.test/records/fixture-record-1", "evidence": "Table 1",
        "validation": "VALID",
    }
    row.update(changes)
    return row


class AgronomyImportTests(TestCase):
    def setUp(self):
        self.dataset = AgriculturalDataset.objects.create(
            identifier="test-usda-fixture", title="Test fixture only", publisher="USDA test publisher",
            version="2026.1", landing_page_url="https://example.test/dataset", doi="10.1234/test.fixture",
            license="CC0-1.0", attribution="Fixture attribution", geographic_scope="United States",
            status=AgriculturalDataset.Status.APPROVED,
        )

    def test_valid_profile_preserves_full_provenance(self):
        audit = import_rows(dataset=self.dataset, rows=[fixture_row()], mapping=MAPPING)
        trait = CropCharacteristic.objects.get()
        self.assertEqual(audit.status, DatasetImport.Status.SUCCEEDED)
        self.assertEqual(trait.original_value, "120")
        self.assertEqual(str(trait.normalized_value), "120.00000000")
        self.assertEqual(trait.dataset.identifier, "test-usda-fixture")
        self.assertEqual(trait.dataset.publisher, "USDA test publisher")
        self.assertEqual(trait.original_dataset_version, "2026.1")
        self.assertEqual(trait.source_license, "CC0-1.0")
        self.assertEqual(trait.source_record_url, "https://example.test/records/fixture-record-1")
        self.assertEqual(trait.dataset.license, "CC0-1.0")
        self.assertEqual(trait.geographic_applicability, "US_SPECIFIC")
        self.dataset.version = "2027.1"
        self.dataset.save(update_fields=["version"])
        trait.refresh_from_db()
        self.assertEqual(trait.original_dataset_version, "2026.1")

    def test_missing_value_is_preserved_as_null_not_defaulted(self):
        audit = import_rows(dataset=self.dataset, rows=[fixture_row(value="", unit="", normalized_unit="")], mapping=MAPPING)
        trait = CropCharacteristic.objects.get()
        self.assertEqual(audit.status, DatasetImport.Status.SUCCEEDED)
        self.assertIsNone(trait.original_value)
        self.assertIsNone(trait.normalized_value)

    def test_numeric_unit_and_type_are_validated(self):
        audit = import_rows(dataset=self.dataset, rows=[fixture_row(unit="", normalized_unit="")], mapping=MAPPING)
        self.assertEqual(audit.status, DatasetImport.Status.PARTIAL)
        self.assertEqual(audit.failed_records, 1)
        self.assertFalse(CropCharacteristic.objects.exists())

    def test_source_specific_unit_vocabulary_is_validated(self):
        audit = import_rows(dataset=self.dataset, rows=[fixture_row(unit="in", normalized_unit="in")], mapping=MAPPING)
        self.assertEqual(audit.status, DatasetImport.Status.PARTIAL)
        self.assertIn("unit 'in'", audit.errors[0]["message"])

    def test_reimport_is_idempotent_and_does_not_duplicate_traits(self):
        first = import_rows(dataset=self.dataset, rows=[fixture_row()], mapping=MAPPING)
        second = import_rows(dataset=self.dataset, rows=[fixture_row()], mapping=MAPPING)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(CropCharacteristic.objects.count(), 1)
        self.assertEqual(DatasetImport.objects.count(), 1)

    def test_conflicting_evidence_is_retained_as_separate_source_records(self):
        audit = import_rows(
            dataset=self.dataset,
            rows=[fixture_row(), fixture_row(record_id="fixture-record-2", value="90", evidence="Table 2")],
            mapping=MAPPING,
        )
        self.assertEqual(audit.imported_records, 2)
        self.assertEqual(CropCharacteristic.objects.filter(characteristic_name="root_depth").count(), 2)

    def test_invalid_source_structure_records_failed_import(self):
        row = fixture_row()
        del row["trait"]
        audit = import_rows(dataset=self.dataset, rows=[row], mapping=MAPPING)
        self.assertEqual(audit.status, DatasetImport.Status.FAILED)
        self.assertEqual(audit.failed_records, 1)
        self.assertFalse(Crop.objects.exists())

    def test_import_rejects_resource_from_another_dataset(self):
        other = AgriculturalDataset.objects.create(
            identifier="other-fixture", title="Other fixture", publisher="Test publisher",
            version="1", landing_page_url="https://example.test/other",
        )
        resource = DatasetResource.objects.create(
            dataset=other, resource_identifier="other-file", title="Other file",
            access_url="https://example.test/other.csv",
        )
        with self.assertRaises(DatasetValidationError):
            import_rows(dataset=self.dataset, resource=resource, rows=[fixture_row()], mapping=MAPPING)

    def test_unapproved_dataset_cannot_import(self):
        self.dataset.status = AgriculturalDataset.Status.PROPOSED
        self.dataset.save(update_fields=["status"])
        with self.assertRaises(DatasetValidationError):
            import_rows(dataset=self.dataset, rows=[fixture_row()], mapping=MAPPING)

    def test_text_and_boolean_normalized_values_are_persisted(self):
        text_mapping = ImportMapping(
            source_crop_identifier="crop_id", crop_name="crop_name", characteristic_name="trait",
            value="value", value_type="value_type", source_record_identifier="record_id",
            original_unit="unit", normalized_unit="normalized_unit",
        )
        audit = import_rows(dataset=self.dataset, rows=[fixture_row(
            trait="growth_form", value="upright", value_type="TEXT", unit="", normalized_unit="",
        )], mapping=text_mapping)
        self.assertEqual(audit.status, DatasetImport.Status.SUCCEEDED)
        self.assertEqual(CropCharacteristic.objects.get().normalized_text, "upright")
        audit = import_rows(dataset=self.dataset, rows=[fixture_row(
            trait="annual", value="false", value_type="BOOLEAN", unit="", normalized_unit="",
            record_id="fixture-record-bool",
        )], mapping=text_mapping)
        self.assertEqual(audit.status, DatasetImport.Status.SUCCEEDED)
        boolean = CropCharacteristic.objects.get(characteristic_name="annual")
        self.assertIs(boolean.normalized_boolean, False)


class AgronomyApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="catalog-user", password="pass")
        self.other_user = User.objects.create_user(username="other-farmer", password="pass")
        self.reviewer = User.objects.create_user(
            username="catalog-reviewer", password="pass", is_staff=True
        )
        self.client = APIClient()
        dataset = AgriculturalDataset.objects.create(
            identifier="test-catalog-fixture", title="Test fixture only", publisher="USDA test publisher",
            version="v1", landing_page_url="https://example.test/dataset", license="CC0",
            attribution="Fixture attribution", status=AgriculturalDataset.Status.APPROVED,
        )
        import_rows(dataset=dataset, rows=[fixture_row(applicability="GENERAL"), fixture_row(
            trait="water_requirement", value="", unit="", normalized_unit="", record_id="fixture-missing"
        )], mapping=MAPPING)
        self.crop = Crop.objects.get()
        # Imported values are source claims only; region readiness requires an
        # explicit reviewer decision.
        trait = CropCharacteristic.objects.get(characteristic_name="root_depth")
        review_evidence(
            reviewer=self.reviewer,
            target_type=ReviewRequest.TargetType.CROP_TRAIT,
            target_id=trait.pk,
            decision=ReviewRequest.Decision.APPROVED,
            rationale="Fixture review for contract testing.",
            evidence_reference="fixture-review-evidence",
            geographic_applicability="GENERAL",
            applicability_justification="Fixture justification, not production evidence.",
        )

    def test_list_requires_region_and_profile_contract_exposes_evidence_and_missing_traits(self):
        self.client.force_authenticate(self.user)
        missing_region = self.client.get("/api/v1/crops/")
        self.assertEqual(missing_region.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("region_code", missing_region.data)
        response = self.client.get("/api/v1/crops/?region_code=EG-GH")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(set(response.data["results"][0]), {"id", "code", "name", "scientific_name", "crop_family", "source_status", "evidence_ids"})
        profile = self.client.get(f"/api/v1/crops/{self.crop.id}/profiles/")
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertIn("water_requirement", profile.data["missing_characteristics"])
        trait = profile.data["characteristics"][0]
        self.assertIn("dataset_identifier", trait["source"])
        self.assertIn("license", trait["source"])
        self.assertNotIn("source_file_name", str(profile.data))

    def test_unauthenticated_catalog_access_is_denied_and_catalog_is_not_farm_scoped(self):
        self.assertEqual(self.client.get("/api/v1/crops/?region_code=EG-GH").status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.force_authenticate(self.other_user)
        # Crop research knowledge is shared, while existing farm endpoints remain owner-scoped.
        self.assertEqual(self.client.get("/api/v1/crops/?region_code=EG-GH").status_code, status.HTTP_200_OK)


class ReviewGateTests(TestCase):
    """A source claim is never a review decision; only approved evidence is region-ready."""

    def setUp(self):
        self.user = User.objects.create_user(username="gate-user", password="pass")
        self.reviewer = User.objects.create_user(
            username="gate-reviewer", password="pass", is_staff=True
        )
        dataset = AgriculturalDataset.objects.create(
            identifier="test-gate-fixture", title="Test fixture only",
            publisher="USDA test publisher", version="v1",
            landing_page_url="https://example.test/gate", license="CC0",
            attribution="Fixture attribution", status=AgriculturalDataset.Status.APPROVED,
        )
        import_rows(dataset=dataset, rows=[fixture_row(applicability="GENERAL")], mapping=MAPPING)
        self.trait = CropCharacteristic.objects.get()
        self.crop = Crop.objects.get()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _list(self):
        return self.client.get("/api/v1/crops/?region_code=EG-GH")

    def _decide(self, decision: str):
        return review_evidence(
            reviewer=self.reviewer,
            target_type=ReviewRequest.TargetType.CROP_TRAIT,
            target_id=self.trait.pk,
            decision=decision,
            rationale="Fixture review for gate testing.",
            evidence_reference="fixture-gate-evidence",
            geographic_applicability="GENERAL" if decision == "APPROVED" else "",
            applicability_justification="Fixture justification, not production evidence.",
        )

    def test_unreviewed_source_claim_is_not_region_ready(self):
        response = self._list()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

        profile = self.client.get(f"/api/v1/crops/{self.crop.id}/profiles/").data
        self.assertEqual(profile["source_status"], "NO_ELIGIBLE_EVIDENCE")
        trait = profile["characteristics"][0]
        self.assertEqual(trait["approval_status"], "PENDING")
        self.assertEqual(trait["approved_geographic_applicability"], "UNKNOWN")
        # The source's own claim is retained and visible, not silently promoted.
        self.assertEqual(trait["geographic_applicability"], "GENERAL")
        self.assertEqual(trait["source_geographic_applicability_claim"], "GENERAL")

    def test_only_a_staff_reviewer_can_approve(self):
        from django.core.exceptions import PermissionDenied

        with self.assertRaises(PermissionDenied):
            review_evidence(
                reviewer=self.user,
                target_type=ReviewRequest.TargetType.CROP_TRAIT,
                target_id=self.trait.pk,
                decision=ReviewRequest.Decision.APPROVED,
                rationale="Self approval attempt.",
                evidence_reference="fixture-gate-evidence",
                geographic_applicability="GENERAL",
                applicability_justification="Fixture justification.",
            )

    def test_approval_makes_the_claim_region_ready(self):
        self._decide(ReviewRequest.Decision.APPROVED)
        self.trait.refresh_from_db()

        self.assertEqual(self.trait.approval_status, "APPROVED")
        self.assertEqual(self.trait.approved_geographic_applicability, "GENERAL")

        response = self._list()
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["source_status"], "VALID")

    def test_rejection_keeps_the_crop_out_of_the_region_catalogue(self):
        self._decide(ReviewRequest.Decision.REJECTED)
        self.trait.refresh_from_db()

        self.assertEqual(self.trait.approval_status, "REJECTED")
        self.assertEqual(self.trait.approved_geographic_applicability, "UNKNOWN")
        self.assertEqual(self._list().data["count"], 0)
