"""Serializers for the environmental data API (Phase 3E).

Only fields a frontend needs are exposed; raw POWER payloads and internal
database identifiers (other than the fetch-job UUID, which is the provenance
handle) are never returned.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.earth_data.models import DataFetchJob, EnvironmentalObservation


class ObservationQuerySerializer(serializers.Serializer):
    """Query parameters for ``GET /farms/{id}/environment/daily/``."""

    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    parameter = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="One code, or a comma-separated list (e.g. T2M,PRECTOTCORR).",
    )


class ScanRequestSerializer(serializers.Serializer):
    """Body for ``POST /farms/{id}/scans/``."""

    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    parameters = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
        help_text="Subset of supported parameter codes; defaults to the MVP set.",
    )
    force = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Re-fetch even when every requested day already has data.",
    )


class ObservationSerializer(serializers.ModelSerializer):
    """One normalised daily value with its units and provenance."""

    date = serializers.DateField(source="observation_date", read_only=True)
    parameter = serializers.CharField(source="source.parameter_code", read_only=True)
    long_name = serializers.CharField(source="source.long_name", read_only=True)
    value = serializers.DecimalField(
        max_digits=10, decimal_places=4, allow_null=True, read_only=True
    )
    unit = serializers.CharField(source="source.units", read_only=True)
    source = serializers.CharField(source="source.provider", read_only=True)
    data_category = serializers.CharField(source="source.data_category", read_only=True)
    time_standard = serializers.CharField(source="source.time_standard", read_only=True)
    fetch_job_id = serializers.UUIDField(allow_null=True, read_only=True)

    class Meta:
        model = EnvironmentalObservation
        fields = [
            "date",
            "parameter",
            "long_name",
            "value",
            "unit",
            "quality_status",
            "source",
            "data_category",
            "time_standard",
            "fetch_job_id",
        ]
        read_only_fields = fields


class DataJobSerializer(serializers.ModelSerializer):
    """Status of one fetch operation (no raw provider payloads)."""

    job_id = serializers.UUIDField(source="id", read_only=True)
    farm_id = serializers.IntegerField(read_only=True)
    status_url = serializers.SerializerMethodField()

    class Meta:
        model = DataFetchJob
        fields = [
            "job_id",
            "farm_id",
            "provider",
            "status",
            "requested_start",
            "requested_end",
            "parameters",
            "days_requested",
            "days_stored",
            "days_missing",
            "error_code",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
            "duration_ms",
            "status_url",
        ]
        read_only_fields = fields

    def get_status_url(self, obj: DataFetchJob) -> str:
        return f"/api/v1/data-jobs/{obj.pk}/"
