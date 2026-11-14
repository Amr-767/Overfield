from django.contrib import admin

from .models import (
    AgriculturalDataset, Crop, CropCharacteristic, CropRotationRule, DatasetImport,
    RegionAgronomyProfile, RegionSeason, RegionSeasonCrop, RotationRecommendation,
)


@admin.register(AgriculturalDataset)
class AgriculturalDatasetAdmin(admin.ModelAdmin):
    list_display = ("identifier", "publisher", "version", "status", "geographic_scope")
    list_filter = ("status",)
    search_fields = ("identifier", "title", "publisher", "doi")


@admin.register(DatasetImport)
class DatasetImportAdmin(admin.ModelAdmin):
    list_display = ("dataset", "status", "total_records", "imported_records", "failed_records", "started_at")
    list_filter = ("status",)
    readonly_fields = ("id", "started_at", "finished_at")


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "scientific_name", "crop_family")
    search_fields = ("code", "name", "scientific_name")


@admin.register(CropCharacteristic)
class CropCharacteristicAdmin(admin.ModelAdmin):
    list_display = ("crop", "characteristic_name", "original_value", "original_unit", "validation_status")
    list_filter = ("validation_status", "geographic_applicability", "dataset")
    search_fields = ("crop__name", "characteristic_name", "source_record_identifier")


@admin.register(RegionAgronomyProfile)
class RegionAgronomyProfileAdmin(admin.ModelAdmin):
    list_display = ("region_code", "calendar_version", "status", "country_code")
    list_filter = ("status", "country_code")
    search_fields = ("region_code", "calendar_version", "source_title")


@admin.register(RegionSeason)
class RegionSeasonAdmin(admin.ModelAdmin):
    list_display = ("profile", "sequence", "season_code", "label")
    list_filter = ("profile",)


@admin.register(RegionSeasonCrop)
class RegionSeasonCropAdmin(admin.ModelAdmin):
    list_display = ("season", "crop", "planting_window", "harvest_window")
    list_filter = ("season__profile",)


@admin.register(CropRotationRule)
class CropRotationRuleAdmin(admin.ModelAdmin):
    list_display = ("identifier", "profile", "rule_type", "crop", "approved")
    list_filter = ("approved", "rule_type", "profile")
    search_fields = ("identifier", "description", "source_title")


@admin.register(RotationRecommendation)
class RotationRecommendationAdmin(admin.ModelAdmin):
    list_display = ("id", "farm", "status", "engine_version", "generated_at")
    list_filter = ("status", "engine_version")
    readonly_fields = ("id", "farm", "requested_by", "engine_version", "input_snapshot", "input_sha256", "assessment", "generated_at")
