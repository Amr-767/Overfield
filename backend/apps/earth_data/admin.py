from django.contrib import admin

from .models import DataFetchJob, DatasetSource, EnvironmentalObservation


@admin.register(DatasetSource)
class DatasetSourceAdmin(admin.ModelAdmin):
    list_display = (
        "parameter_code",
        "provider",
        "product",
        "units",
        "daily_aggregation",
        "first_available_date",
        "is_active",
    )
    list_filter = ("provider", "is_active", "data_category", "daily_aggregation")
    search_fields = ("parameter_code", "long_name")


@admin.register(DataFetchJob)
class DataFetchJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "farm",
        "status",
        "requested_start",
        "requested_end",
        "days_stored",
        "days_missing",
        "created_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("farm__name", "error_code")
    readonly_fields = ("id", "created_at")


@admin.register(EnvironmentalObservation)
class EnvironmentalObservationAdmin(admin.ModelAdmin):
    list_display = ("farm", "source", "observation_date", "value", "quality_status")
    list_filter = ("quality_status", "source__parameter_code")
    search_fields = ("farm__name",)
    date_hierarchy = "observation_date"
