from django.db.models import Q
from rest_framework import serializers

from .models import AgriculturalDataset, Crop, CropCharacteristic, GeographicApplicability


class CropListSerializer(serializers.ModelSerializer):
    source_status = serializers.SerializerMethodField()
    evidence_ids = serializers.SerializerMethodField()

    class Meta:
        model = Crop
        fields = ("id", "code", "name", "scientific_name", "crop_family", "source_status", "evidence_ids")

    def _eligible_characteristics(self, obj):
        region = self.context.get("request").query_params.get("region_code", "") if self.context.get("request") else ""
        return [
            trait for trait in obj.characteristics.all()
            if trait.approval_status == "APPROVED"
            and trait.validation_status == "VALID"
            and trait.original_value is not None
            and trait.dataset.status == AgriculturalDataset.Status.APPROVED
            and trait.dataset_import.status == "SUCCEEDED"
            and (
                trait.approved_geographic_applicability in {GeographicApplicability.GENERAL, GeographicApplicability.TRANSFERABLE_LIMITED}
                or (trait.approved_geographic_applicability == GeographicApplicability.DIRECT and trait.geographic_scope.casefold() == region.casefold())
            )
        ]

    def get_source_status(self, obj):
        return "VALID" if self._eligible_characteristics(obj) else "NO_ELIGIBLE_EVIDENCE"

    def get_evidence_ids(self, obj):
        return [trait.source_record_identifier for trait in self._eligible_characteristics(obj)]


class CropCharacteristicSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()

    class Meta:
        model = CropCharacteristic
        fields = (
            "id", "source_crop_identifier", "cultivar_or_variety", "characteristic_name",
            "value_type", "original_value", "original_unit", "normalized_value", "normalized_text",
            "normalized_boolean", "normalized_unit",
            "temporal_applicability", "geographic_scope", "geographic_applicability",
            "source_geographic_applicability_claim", "approval_status",
            "approved_geographic_applicability", "applicability_justification",
            "source_record_identifier", "source_record_url", "evidence_reference", "validation_status",
            "imported_at", "source",
        )

    def get_source(self, obj):
        return {
            "dataset_identifier": obj.original_dataset_identifier,
            "publisher": obj.original_publisher,
            "dataset_version": obj.original_dataset_version or None, "doi": obj.source_doi or None,
            "license": obj.source_license or None, "attribution": obj.source_attribution or None,
            "landing_page_url": obj.original_dataset_landing_page_url,
            "resource_identifier": obj.source_resource_identifier or None,
            "resource_url": obj.source_resource_url or None,
        }


class CropProfileSerializer(CropListSerializer):
    characteristics = CropCharacteristicSerializer(many=True, read_only=True)
    missing_characteristics = serializers.SerializerMethodField()

    class Meta(CropListSerializer.Meta):
        fields = CropListSerializer.Meta.fields + ("characteristics", "missing_characteristics")

    def get_missing_characteristics(self, obj):
        return sorted({
            row.characteristic_name for row in obj.characteristics.all()
            if row.original_value is None
        })
