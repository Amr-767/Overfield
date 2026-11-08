"""Geometry validation and geodesic measurement for farm boundaries.

GeoJSON is the API interchange format (ADR-010) and coordinates are always
``[longitude, latitude]``. All metric area calculations go through PostGIS by
casting the stored SRID 4326 geometry to ``geography`` (ADR-003); degrees are
never treated as metres.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point
from django.db import connection

SRID = 4326
"""Storage and interchange SRID: WGS 84 longitude/latitude (degrees)."""

MAX_FARM_AREA_HECTARES = Decimal("10000.0000")
"""Reject implausible farm sizes; also guards against swapped coordinates."""

LON_RANGE = (-180.0, 180.0)
LAT_RANGE = (-90.0, 90.0)

CLOSURE_TOLERANCE = 1e-9

GEOJSON_GEOMETRY_TYPES = ("Polygon", "MultiPolygon")


class GeometryValidationError(ValueError):
    """Raised when incoming GeoJSON cannot be used as a farm boundary."""

    def __init__(self, message: str, field: str = "boundary"):
        super().__init__(message)
        self.message = message
        self.field = field


def _as_mapping(payload: Any) -> dict:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise GeometryValidationError("Invalid GeoJSON: not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise GeometryValidationError("Invalid GeoJSON: expected an object.")
    if payload.get("type") == "Feature":
        geometry = payload.get("geometry")
        if not isinstance(geometry, dict):
            raise GeometryValidationError("Invalid GeoJSON: Feature has no geometry.")
        payload = geometry
    return payload


def _iter_positions(coordinates: Any):
    """Yield every position in a Polygon/MultiPolygon coordinate array."""
    if not isinstance(coordinates, (list, tuple)):
        raise GeometryValidationError("Invalid GeoJSON: coordinates must be an array.")
    for item in coordinates:
        if isinstance(item, (list, tuple)) and item and isinstance(item[0], (int, float)):
            yield item
        else:
            yield from _iter_positions(item)


def _validate_position(position: Any) -> None:
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        raise GeometryValidationError("Invalid GeoJSON: each position needs longitude and latitude.")
    lon, lat = position[0], position[1]
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        raise GeometryValidationError("Invalid GeoJSON: coordinates must be numbers.")
    if isinstance(lon, bool) or isinstance(lat, bool):
        raise GeometryValidationError("Invalid GeoJSON: coordinates must be numbers.")
    if not (LON_RANGE[0] <= float(lon) <= LON_RANGE[1]):
        raise GeometryValidationError(
            f"Invalid longitude {lon}: must be within [-180, 180] "
            "(GeoJSON order is [longitude, latitude])."
        )
    if not (LAT_RANGE[0] <= float(lat) <= LAT_RANGE[1]):
        raise GeometryValidationError(
            f"Invalid latitude {lat}: must be within [-90, 90] "
            "(GeoJSON order is [longitude, latitude])."
        )


def _validate_rings(coordinates: Any) -> None:
    """Check ring shape and closure before GEOS silently repairs anything."""
    polygons = [coordinates] if _looks_like_polygon(coordinates) else coordinates
    for polygon in polygons:
        if not isinstance(polygon, (list, tuple)) or not polygon:
            raise GeometryValidationError("Invalid polygon: it has no linear rings.")
        for ring in polygon:
            if not isinstance(ring, (list, tuple)):
                raise GeometryValidationError("Invalid polygon: a linear ring must be an array.")
            if len(ring) < 4:
                raise GeometryValidationError(
                    "Invalid polygon: a linear ring needs at least 4 positions."
                )
            first, last = ring[0], ring[-1]
            if (
                abs(float(first[0]) - float(last[0])) > CLOSURE_TOLERANCE
                or abs(float(first[1]) - float(last[1])) > CLOSURE_TOLERANCE
            ):
                raise GeometryValidationError(
                    "Invalid polygon: geometry is not closed (first and last position must match)."
                )


def _looks_like_polygon(coordinates: Any) -> bool:
    return (
        isinstance(coordinates, (list, tuple))
        and bool(coordinates)
        and isinstance(coordinates[0], (list, tuple))
        and bool(coordinates[0])
        and isinstance(coordinates[0][0], (list, tuple))
        and bool(coordinates[0][0])
        and isinstance(coordinates[0][0][0], (int, float))
    )


def parse_boundary_geojson(payload: Any, field: str = "boundary") -> tuple[MultiPolygon, Decimal]:
    """Validate GeoJSON and return ``(multipolygon, area_hectares)``.

    Raises :class:`GeometryValidationError` for malformed, empty, out-of-range,
    unclosed, self-intersecting, zero-area or implausibly large geometries.
    """
    data = _as_mapping(payload)
    geometry_type = data.get("type")
    if geometry_type not in GEOJSON_GEOMETRY_TYPES:
        raise GeometryValidationError(
            f"Invalid geometry type {geometry_type!r}: expected 'Polygon' or 'MultiPolygon'.",
            field=field,
        )
    coordinates = data.get("coordinates")
    if not coordinates:
        raise GeometryValidationError("Invalid geometry: coordinates are empty.", field=field)

    for position in _iter_positions(coordinates):
        _validate_position(position)
    _validate_rings(coordinates)

    try:
        geometry = GEOSGeometry(json.dumps({"type": geometry_type, "coordinates": coordinates}), srid=SRID)
    except Exception as exc:  # GEOS raises several exception types
        raise GeometryValidationError(f"Invalid geometry: {exc}", field=field) from exc

    if geometry.empty:
        raise GeometryValidationError("Invalid geometry: the polygon is empty.", field=field)
    if not geometry.valid:
        raise GeometryValidationError(
            "Invalid polygon: geometry is self-intersecting or otherwise invalid "
            "(check for crossing edges or duplicate vertices).",
            field=field,
        )
    if geometry.area <= 0:
        raise GeometryValidationError("Invalid polygon: it has zero area.", field=field)

    multipolygon = geometry if isinstance(geometry, MultiPolygon) else MultiPolygon(geometry, srid=SRID)
    multipolygon.srid = SRID

    area_hectares = geodesic_area_hectares(multipolygon)
    if area_hectares <= 0:
        raise GeometryValidationError("Invalid polygon: computed area is zero.", field=field)
    if area_hectares > MAX_FARM_AREA_HECTARES:
        raise GeometryValidationError(
            f"Calculated area exceeds the maximum allowed ({MAX_FARM_AREA_HECTARES} ha). "
            "Check the coordinate order [longitude, latitude] and the boundary size.",
            field=field,
        )
    return multipolygon, area_hectares


def parse_location_geojson(payload: Any, field: str = "location") -> Point:
    """Validate a GeoJSON ``Point`` (``[longitude, latitude]``)."""
    data = _as_mapping(payload)
    if data.get("type") != "Point":
        raise GeometryValidationError("Invalid location: expected a GeoJSON 'Point'.", field=field)
    coordinates = data.get("coordinates")
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        raise GeometryValidationError(
            "Invalid location: a Point needs [longitude, latitude].", field=field
        )
    _validate_position(coordinates)
    point = Point(float(coordinates[0]), float(coordinates[1]), srid=SRID)
    point.srid = SRID
    return point


def geodesic_area_hectares(geometry: GEOSGeometry) -> Decimal:
    """Area in hectares using PostGIS geography (metres, not degrees)."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ST_Area(ST_GeomFromEWKB(%s)::geography) / 10000.0;",
            [geometry.ewkb],
        )
        value = cursor.fetchone()[0]
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def boundary_centroid(geometry: GEOSGeometry) -> Point:
    """Planar centroid of the SRID 4326 geometry, used as a map marker."""
    centroid = geometry.centroid
    centroid.srid = SRID
    return centroid


def geojson_dict(geometry: GEOSGeometry | None) -> dict | None:
    """Serialize a geometry field to a GeoJSON mapping for API responses."""
    if geometry is None:
        return None
    return json.loads(geometry.geojson)
