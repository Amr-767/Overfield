"""Serializers, validation and permissions for farms, zones and farmer context."""

from __future__ import annotations

from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers
from rest_framework.fields import empty

from domain_services.geometry import (
    MAX_FARM_AREA_HECTARES,
    GeometryValidationError,
    boundary_centroid,
    geojson_dict,
    parse_boundary_geojson,
    parse_location_geojson,
)

from .models import Farm, FarmCropHistory, FarmerContext, FarmZone

PRIORITY_KEYS = (
    "water_conservation",
    "soil_regeneration",
    "market_income",
    "forage_value",
)
CONSTRAINT_KEYS = ("equipment", "seed_availability", "labor_availability")


def _geometry_error(exc: GeometryValidationError) -> serializers.ValidationError:
    return serializers.ValidationError({exc.field: [exc.message]})


def _validate_country_code(value: str) -> str:
    if value in (None, ""):
        return ""
    if len(value) != 2 or not value.isalpha():
        raise serializers.ValidationError("Country code must be a 2-letter ISO code (e.g. 'EG').")
    return value.upper()


def _validate_timezone(value: str) -> str:
    if not value:
        return "UTC"
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise serializers.ValidationError(f"Unknown timezone {value!r}.") from exc
    return value


class FarmSerializer(serializers.ModelSerializer):
    """Read representation; area is always the backend-computed value."""

    boundary = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    area_hectares = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    spatial_precision = serializers.ReadOnlyField()
    zone_count = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "country_code",
            "region_code",
            "boundary",
            "location",
            "area_hectares",
            "area_source",
            "geometry_source",
            "spatial_precision",
            "timezone",
            "zone_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_boundary(self, obj: Farm) -> dict | None:
        return geojson_dict(obj.boundary)

    def get_location(self, obj: Farm) -> dict | None:
        return geojson_dict(obj.location)

    def get_zone_count(self, obj: Farm) -> int:
        return obj.zones.count()


class _FarmWriteMixin(serializers.Serializer):
    """Shared field definitions and geometry resolution for create/update."""

    name = serializers.CharField(max_length=120)
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True, default="")
    region_code = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    timezone = serializers.CharField(max_length=64, required=False, default="UTC")
    boundary = serializers.JSONField(required=False, allow_null=True)
    location = serializers.JSONField(required=False, allow_null=True)
    farmer_reported_area_hectares = serializers.DecimalField(
        max_digits=14,
        decimal_places=4,
        required=False,
        allow_null=True,
        min_value=Decimal("0.0001"),
        write_only=True,
    )

    def validate_country_code(self, value: str) -> str:
        return _validate_country_code(value)

    def validate_timezone(self, value: str) -> str:
        return _validate_timezone(value)


class FarmCreateSerializer(_FarmWriteMixin):
    """Create a farm from a boundary polygon, or from a location + reported area."""

    def validate(self, attrs: dict) -> dict:
        boundary = attrs.pop("boundary", None)
        location = attrs.pop("location", None)
        reported_area = attrs.pop("farmer_reported_area_hectares", None)

        if boundary:
            try:
                geometry, area = parse_boundary_geojson(boundary)
                marker = (
                    parse_location_geojson(location) if location else boundary_centroid(geometry)
                )
            except GeometryValidationError as exc:
                raise _geometry_error(exc) from exc
            attrs.update(
                boundary=geometry,
                location=marker,
                area_hectares=area,
                area_source=Farm.AreaSource.GEOMETRY_DERIVED,
                geometry_source=Farm.GeometrySource.BOUNDARY,
            )
            return attrs

        if not location:
            raise serializers.ValidationError(
                {
                    "boundary": [
                        "Provide a GeoJSON boundary polygon, or a location point with "
                        "farmer_reported_area_hectares for the low-precision fallback."
                    ]
                }
            )
        if reported_area is None:
            raise serializers.ValidationError(
                {
                    "farmer_reported_area_hectares": [
                        "Required when only a location point is supplied "
                        "(point-only farms cannot have a computed area)."
                    ]
                }
            )
        if reported_area > MAX_FARM_AREA_HECTARES:
            raise serializers.ValidationError(
                {
                    "farmer_reported_area_hectares": [
                        f"Reported area exceeds the maximum allowed ({MAX_FARM_AREA_HECTARES} ha)."
                    ]
                }
            )
        try:
            marker = parse_location_geojson(location)
        except GeometryValidationError as exc:
            raise _geometry_error(exc) from exc

        attrs.update(
            boundary=None,
            location=marker,
            area_hectares=reported_area,
            area_source=Farm.AreaSource.FARMER_REPORTED,
            geometry_source=Farm.GeometrySource.LOCATION_POINT,
        )
        return attrs

    def create(self, validated_data: dict) -> Farm:
        return Farm.objects.create(owner=self.context["request"].user, **validated_data)


class FarmUpdateSerializer(_FarmWriteMixin):
    """PATCH metadata, replace the boundary, or move the location marker.

    ``area_hectares`` is never accepted from the client; supplying a new
    boundary recomputes it from the geometry.
    """

    name = serializers.CharField(max_length=120, required=False)

    def validate(self, attrs: dict) -> dict:
        boundary = attrs.pop("boundary", empty)
        location = attrs.pop("location", empty)
        reported_area = attrs.pop("farmer_reported_area_hectares", None)

        if boundary is not empty and boundary is not None:
            try:
                geometry, area = parse_boundary_geojson(boundary)
            except GeometryValidationError as exc:
                raise _geometry_error(exc) from exc
            attrs.update(
                boundary=geometry,
                area_hectares=area,
                area_source=Farm.AreaSource.GEOMETRY_DERIVED,
                geometry_source=Farm.GeometrySource.BOUNDARY,
            )
            if location is empty or location is None:
                attrs["location"] = boundary_centroid(geometry)
        elif boundary is None:
            raise serializers.ValidationError(
                {"boundary": ["A farm boundary cannot be cleared; supply a new polygon instead."]}
            )

        if location is not empty and location is not None:
            try:
                attrs["location"] = parse_location_geojson(location)
            except GeometryValidationError as exc:
                raise _geometry_error(exc) from exc

        if reported_area is not None and "boundary" not in attrs:
            instance: Farm = self.instance
            if instance.geometry_source != Farm.GeometrySource.LOCATION_POINT:
                raise serializers.ValidationError(
                    {
                        "farmer_reported_area_hectares": [
                            "Reported area only applies to point-only farms; "
                            "boundary farms use the computed area."
                        ]
                    }
                )
            if reported_area > MAX_FARM_AREA_HECTARES:
                raise serializers.ValidationError(
                    {
                        "farmer_reported_area_hectares": [
                            f"Reported area exceeds the maximum allowed ({MAX_FARM_AREA_HECTARES} ha)."
                        ]
                    }
                )
            attrs.update(area_hectares=reported_area, area_source=Farm.AreaSource.FARMER_REPORTED)

        return attrs

    def update(self, instance: Farm, validated_data: dict) -> Farm:
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class BoundaryValidationSerializer(serializers.Serializer):
    """Read-only validation payload: echoes the parsed area without saving."""

    boundary = serializers.JSONField()


class FarmZoneSerializer(serializers.ModelSerializer):
    boundary = serializers.SerializerMethodField()

    class Meta:
        model = FarmZone
        fields = ["id", "farm", "name", "boundary", "area_hectares", "notes", "created_at"]
        read_only_fields = ["id", "farm", "boundary", "area_hectares", "created_at"]

    def get_boundary(self, obj: FarmZone) -> dict | None:
        return geojson_dict(obj.boundary)


class FarmZoneCreateSerializer(serializers.Serializer):
    """Create a zone that lies wholly inside its farm boundary."""

    name = serializers.CharField(max_length=80)
    boundary = serializers.JSONField()
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate(self, attrs: dict) -> dict:
        farm: Farm = self.context["farm"]
        try:
            geometry, area = parse_boundary_geojson(attrs["boundary"])
        except GeometryValidationError as exc:
            raise _geometry_error(exc) from exc

        if farm.boundary is None:
            raise serializers.ValidationError(
                {"boundary": ["Zones require a farm with a drawn boundary."]}
            )
        if not farm.boundary.covers(geometry):
            raise serializers.ValidationError(
                {"boundary": ["Zone geometry must lie wholly inside the farm boundary."]}
            )
        if area > farm.area_hectares:
            raise serializers.ValidationError(
                {"boundary": ["Zone area cannot exceed the farm area."]}
            )
        attrs.update(farm=farm, boundary=geometry, area_hectares=area)
        return attrs

    def create(self, validated_data: dict) -> FarmZone:
        return FarmZone.objects.create(**validated_data)


class FarmCropHistorySerializer(serializers.ModelSerializer):
    """Contract field names: ``season`` and ``crop``."""

    season = serializers.CharField(source="season_label")
    crop = serializers.CharField(source="crop_name")

    class Meta:
        model = FarmCropHistory
        fields = ["id", "season", "crop", "crop_code", "source", "notes"]
        read_only_fields = ["id"]


class FarmerContextSerializer(serializers.ModelSerializer):
    """Farmer inputs. Every measurement is optional; ``null`` means unknown."""

    farm_id = serializers.IntegerField(read_only=True)
    current_crops = FarmCropHistorySerializer(many=True, required=False, source="crops")

    class Meta:
        model = FarmerContext
        fields = [
            "farm_id",
            "soil_source",
            "texture_class",
            "ph",
            "organic_carbon_percent",
            "nitrogen_ppm",
            "phosphorus_ppm",
            "potassium_ppm",
            "sampling_depth_cm",
            "sampling_method",
            "lab_name",
            "sample_date",
            "water_source",
            "irrigation_available",
            "irrigation_type",
            "water_reliability",
            "priorities",
            "constraints",
            "current_crops",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["farm_id", "created_at", "updated_at"]

    def validate_ph(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("14")):
            raise serializers.ValidationError("Soil pH must be between 0 and 14.")
        return value

    def validate_organic_carbon_percent(self, value):
        if value is not None and not (Decimal("0") <= value <= Decimal("100")):
            raise serializers.ValidationError("Organic carbon percent must be between 0 and 100.")
        return value

    def validate_priorities(self, value: dict) -> dict:
        if value in (None, {}):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("priorities must be an object of named weights.")
        unknown = set(value) - set(PRIORITY_KEYS)
        if unknown:
            raise serializers.ValidationError(
                f"Unknown priority keys: {sorted(unknown)}. Allowed: {list(PRIORITY_KEYS)}."
            )
        weights = {}
        for key, raw in value.items():
            try:
                weight = Decimal(str(raw))
            except Exception as exc:
                raise serializers.ValidationError(f"Priority {key!r} must be a number.") from exc
            if weight < 0:
                raise serializers.ValidationError(f"Priority {key!r} must be non-negative.")
            weights[key] = float(weight)
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise serializers.ValidationError(
                f"Priority weights must sum to 1 when supplied (got {round(total, 4)})."
            )
        return weights

    def validate_constraints(self, value: dict) -> dict:
        if value in (None, {}):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("constraints must be an object.")
        unknown = set(value) - set(CONSTRAINT_KEYS)
        if unknown:
            raise serializers.ValidationError(
                f"Unknown constraint keys: {sorted(unknown)}. Allowed: {list(CONSTRAINT_KEYS)}."
            )
        equipment = value.get("equipment")
        if equipment is not None and not isinstance(equipment, list):
            raise serializers.ValidationError("constraints.equipment must be a list.")
        return value

    def update(self, instance: FarmerContext, validated_data: dict) -> FarmerContext:
        crops = validated_data.pop("crops", None)
        instance = super().update(instance, validated_data)
        if crops is not None:
            instance.crops.all().delete()
            for index, crop in enumerate(crops):
                FarmCropHistory.objects.create(
                    context=instance, sequence=index, **crop
                )
        return instance
