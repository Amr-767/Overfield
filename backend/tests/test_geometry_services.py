"""Geometry validation and geodesic area tests (Phase 2B)."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.gis.geos import MultiPolygon
from django.test import TestCase

from domain_services.geometry import (
    MAX_FARM_AREA_HECTARES,
    GeometryValidationError,
    geodesic_area_hectares,
    parse_boundary_geojson,
    parse_location_geojson,
)

# ~0.0021 deg lon x 0.0017 deg lat near the Nile Delta: about 3.79 ha.
KNOWN_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [30.9501, 30.7901],
            [30.9522, 30.7901],
            [30.9522, 30.7918],
            [30.9501, 30.7918],
            [30.9501, 30.7901],
        ]
    ],
}


class GeometryValidationTests(TestCase):
    def test_valid_polygon_is_normalised_to_multipolygon(self) -> None:
        geometry, area = parse_boundary_geojson(KNOWN_POLYGON)
        self.assertIsInstance(geometry, MultiPolygon)
        self.assertEqual(geometry.srid, 4326)
        self.assertAlmostEqual(float(area), 3.7882, delta=0.01)

    def test_area_is_geodesic_not_degrees(self) -> None:
        _, area = parse_boundary_geojson(KNOWN_POLYGON)
        # Raw degree-squared area of this ring is ~3.57e-6; metres must be used.
        self.assertGreater(area, Decimal("1"))
        self.assertLess(area, Decimal("10"))

    def test_feature_wrapper_is_accepted(self) -> None:
        payload = {"type": "Feature", "properties": {}, "geometry": KNOWN_POLYGON}
        geometry, _ = parse_boundary_geojson(payload)
        self.assertEqual(geometry.geom_type, "MultiPolygon")

    def test_multipolygon_is_accepted(self) -> None:
        payload = {"type": "MultiPolygon", "coordinates": [KNOWN_POLYGON["coordinates"]]}
        geometry, area = parse_boundary_geojson(payload)
        self.assertIsInstance(geometry, MultiPolygon)
        self.assertAlmostEqual(float(area), 3.7882, delta=0.01)

    def test_unclosed_ring_is_rejected(self) -> None:
        payload = {
            "type": "Polygon",
            "coordinates": [
                [[30.9501, 30.7901], [30.9522, 30.7901], [30.9522, 30.7918], [30.9501, 30.7918]]
            ],
        }
        with self.assertRaises(GeometryValidationError) as ctx:
            parse_boundary_geojson(payload)
        self.assertIn("not closed", str(ctx.exception))

    def test_self_intersecting_polygon_is_rejected(self) -> None:
        bowtie = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]],
        }
        with self.assertRaises(GeometryValidationError) as ctx:
            parse_boundary_geojson(bowtie)
        self.assertIn("self-intersecting", str(ctx.exception))

    def test_longitude_out_of_range_is_rejected(self) -> None:
        payload = {
            "type": "Polygon",
            "coordinates": [[[200, 30], [201, 30], [201, 31], [200, 31], [200, 30]]],
        }
        with self.assertRaises(GeometryValidationError) as ctx:
            parse_boundary_geojson(payload)
        self.assertIn("longitude", str(ctx.exception))

    def test_latitude_out_of_range_is_rejected(self) -> None:
        payload = {
            "type": "Polygon",
            "coordinates": [[[30, 95], [31, 95], [31, 96], [30, 96], [30, 95]]],
        }
        with self.assertRaises(GeometryValidationError) as ctx:
            parse_boundary_geojson(payload)
        self.assertIn("latitude", str(ctx.exception))

    def test_empty_coordinates_are_rejected(self) -> None:
        with self.assertRaises(GeometryValidationError):
            parse_boundary_geojson({"type": "Polygon", "coordinates": []})

    def test_wrong_geometry_type_is_rejected(self) -> None:
        with self.assertRaises(GeometryValidationError):
            parse_boundary_geojson({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})

    def test_zero_area_polygon_is_rejected(self) -> None:
        payload = {
            "type": "Polygon",
            "coordinates": [[[30, 30], [30, 30], [30, 30], [30, 30]]],
        }
        with self.assertRaises(GeometryValidationError):
            parse_boundary_geojson(payload)

    def test_ring_with_too_few_positions_is_rejected(self) -> None:
        payload = {"type": "Polygon", "coordinates": [[[30, 30], [31, 31], [30, 30]]]}
        with self.assertRaises(GeometryValidationError) as ctx:
            parse_boundary_geojson(payload)
        self.assertIn("at least 4 positions", str(ctx.exception))

    def test_implausibly_large_polygon_is_rejected(self) -> None:
        # ~0.2 deg square near the equator is ~490 km2 (~49,000 ha) > cap.
        payload = {
            "type": "Polygon",
            "coordinates": [[[30, 0], [30.2, 0], [30.2, 0.2], [30, 0.2], [30, 0]]],
        }
        with self.assertRaises(GeometryValidationError) as ctx:
            parse_boundary_geojson(payload)
        self.assertIn("maximum allowed", str(ctx.exception))
        self.assertGreater(float(MAX_FARM_AREA_HECTARES), 0)

    def test_coordinate_order_longitude_first(self) -> None:
        geometry, _ = parse_boundary_geojson(KNOWN_POLYGON)
        centroid = geometry.centroid
        # [lon, lat] ordering: 30.95 is the longitude, 30.79 the latitude.
        self.assertAlmostEqual(centroid.x, 30.95115, places=5)
        self.assertAlmostEqual(centroid.y, 30.79095, places=5)

    def test_location_point_longitude_first(self) -> None:
        point = parse_location_geojson({"type": "Point", "coordinates": [31.2357, 30.0444]})
        self.assertEqual(point.srid, 4326)
        self.assertAlmostEqual(point.x, 31.2357)
        self.assertAlmostEqual(point.y, 30.0444)

    def test_string_geojson_is_accepted(self) -> None:
        import json

        geometry, _ = parse_boundary_geojson(json.dumps(KNOWN_POLYGON))
        self.assertEqual(geometry.geom_type, "MultiPolygon")


class GeodesicAreaTests(TestCase):
    def test_known_geometry_area_matches_postgis_geography(self) -> None:
        geometry, area = parse_boundary_geojson(KNOWN_POLYGON)
        self.assertAlmostEqual(float(geodesic_area_hectares(geometry)), float(area), places=3)

    def test_one_degree_box_near_equator_is_about_12300_hectares(self) -> None:
        # 1 deg x 1 deg at the equator ~= 111.32 km x 110.57 km ~= 12,300 km2
        box = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        }
        with self.assertRaises(GeometryValidationError):
            # Exceeds the 10,000 ha cap, which also proves metres are used.
            parse_boundary_geojson(box)
        geometry, _ = parse_boundary_geojson(KNOWN_POLYGON)
        self.assertIsNotNone(geometry)
