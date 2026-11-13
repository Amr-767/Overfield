"""Soil indicator tests (Phase 4C) — deterministic fixtures, no network."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase

from apps.indicators.contract import Confidence, Freshness, IndicatorStatus
from apps.indicators.services.soil import (
    ACIDIC,
    ALKALINE,
    CORE_PROPERTIES,
    NEUTRAL,
    SoilProfile,
    calculate_soil_indicator,
    ph_band,
    sample_freshness,
)

TODAY = date(2026, 11, 9)


def full_profile(**overrides) -> SoilProfile:
    values = dict(
        soil_source="LAB_TEST",
        texture_class="clay_loam",
        ph=Decimal("7.80"),
        organic_carbon_percent=Decimal("1.20"),
        nitrogen_ppm=Decimal("22.50"),
        phosphorus_ppm=Decimal("11.00"),
        potassium_ppm=Decimal("180.00"),
        sampling_depth_cm=30,
        sampling_method="composite",
        lab_name="Delta Soil Lab",
        sample_date=date(2026, 3, 15),
    )
    values.update(overrides)
    return SoilProfile(**values)


def build(profile: SoilProfile | None, today: date = TODAY):
    return calculate_soil_indicator(profile=profile, today=today)


class SoilPropertyTests(SimpleTestCase):
    def test_full_lab_profile_reports_each_property_independently(self) -> None:
        result = build(full_profile())
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.OK)
        self.assertEqual(result.confidence, Confidence.HIGH)
        self.assertEqual(result.completeness.properties_present, len(CORE_PROPERTIES))
        self.assertEqual(result.completeness.ratio, Decimal("1.0000"))
        self.assertIsNone(result.score)

        self.assertEqual(measurements["ph"].value, Decimal("7.80"))
        self.assertEqual(measurements["ph"].unit, "pH")
        self.assertEqual(measurements["ph"].interpretation, ALKALINE)  # 7.80 > 7.5
        self.assertEqual(measurements["organic_carbon_percent"].unit, "%")
        self.assertEqual(measurements["nitrogen_ppm"].unit, "ppm")
        self.assertEqual(measurements["phosphorus_ppm"].unit, "ppm")
        self.assertEqual(measurements["potassium_ppm"].unit, "ppm")
        self.assertEqual(measurements["texture_class"].value, "clay_loam")
        self.assertIn("qualitative", measurements["texture_class"].interpretation)

    def test_ph_bands_are_descriptive_only(self) -> None:
        self.assertEqual(ph_band(Decimal("5.99")), ACIDIC)
        self.assertEqual(ph_band(Decimal("6.00")), NEUTRAL)
        self.assertEqual(ph_band(Decimal("7.50")), NEUTRAL)
        self.assertEqual(ph_band(Decimal("7.51")), ALKALINE)
        self.assertIsNone(ph_band(None))

    def test_organic_carbon_has_no_invented_threshold(self) -> None:
        result = build(full_profile())
        carbon = next(m for m in result.measurements if m.name == "organic_carbon_percent")
        self.assertEqual(carbon.value, Decimal("1.20"))
        self.assertIsNone(carbon.interpretation)
        self.assertTrue(any("single sample" in text for text in result.limitations))

    def test_npk_preserves_method_and_is_not_classified(self) -> None:
        result = build(full_profile())
        for name in ("nitrogen_ppm", "phosphorus_ppm", "potassium_ppm"):
            measurement = next(m for m in result.measurements if m.name == name)
            self.assertEqual(measurement.unit, "ppm")
            self.assertEqual(measurement.method, "composite")
            self.assertIsNone(measurement.interpretation)  # no deficient/sufficient label
        self.assertTrue(any("extraction method" in text for text in result.limitations))

    def test_provenance_and_sampling_metadata_are_preserved(self) -> None:
        result = build(full_profile())
        context = {item.name: item for item in result.context}

        self.assertEqual(context["sample_date"].value, "2026-03-15")
        self.assertEqual(context["sampling_depth_cm"].value, 30)
        self.assertEqual(context["sampling_method"].value, "composite")
        self.assertEqual(context["lab_name"].value, "Delta Soil Lab")
        self.assertTrue(all(m.source == "LAB_TEST" for m in result.measurements))
        self.assertTrue(all(m.quality == "LAB_TEST" for m in result.measurements))


class SoilFreshnessTests(SimpleTestCase):
    def test_bands(self) -> None:
        self.assertEqual(sample_freshness(date(2026, 6, 1), TODAY), Freshness.FRESH)   # 5 months
        self.assertEqual(sample_freshness(date(2025, 6, 1), TODAY), Freshness.AGEING)  # 17 months
        self.assertEqual(sample_freshness(date(2024, 1, 1), TODAY), Freshness.STALE)   # 34 months
        self.assertEqual(sample_freshness(None, TODAY), Freshness.UNKNOWN)

    def test_future_sample_date_is_flagged_not_fresh(self) -> None:
        self.assertEqual(sample_freshness(date(2027, 1, 1), TODAY), Freshness.FUTURE)
        result = build(full_profile(sample_date=date(2027, 1, 1)))
        self.assertEqual(result.period.freshness, Freshness.FUTURE)
        self.assertTrue(any("future" in text for text in result.limitations))
        self.assertNotEqual(result.confidence, Confidence.HIGH)

    def test_missing_sample_date_is_unknown(self) -> None:
        result = build(full_profile(sample_date=None))
        # No sample date means there is no observation period to describe, so the
        # contract reports `period: null` rather than inventing a window.
        self.assertIsNone(result.period)
        # Freshness is still computed and surfaced through the driver and summary.
        freshness_driver = next(
            driver for driver in result.drivers if driver.name == "Sample freshness"
        )
        self.assertEqual(freshness_driver.value, Freshness.UNKNOWN.value)
        self.assertIn("sample date not recorded", result.summary)
        self.assertIn("sample_date", {item.name for item in result.missing})
        self.assertTrue(any("sample date" in text for text in result.limitations))

    def test_stale_lab_sample_lowers_confidence(self) -> None:
        fresh = build(full_profile(sample_date=date(2026, 6, 1)))
        stale = build(full_profile(sample_date=date(2024, 1, 1)))
        self.assertEqual(fresh.confidence, Confidence.HIGH)
        self.assertEqual(stale.confidence, Confidence.LOW)


class SoilCompletenessTests(SimpleTestCase):
    def test_partial_profile_is_partial_with_missing_list(self) -> None:
        result = build(full_profile(ph=Decimal("7.8"), texture_class="clay_loam",
                                    organic_carbon_percent=None, nitrogen_ppm=None,
                                    phosphorus_ppm=None, potassium_ppm=None))
        self.assertEqual(result.status, IndicatorStatus.PARTIAL)
        self.assertEqual(result.completeness.properties_present, 2)
        missing = {item.name for item in result.missing}
        self.assertEqual(
            missing,
            {"organic_carbon_percent", "nitrogen_ppm", "phosphorus_ppm", "potassium_ppm"},
        )
        self.assertEqual(result.confidence, Confidence.LOW)  # 2/6 properties

    def test_no_context_returns_insufficient_data(self) -> None:
        result = build(None)
        self.assertEqual(result.status, IndicatorStatus.INSUFFICIENT_DATA)
        self.assertEqual(result.confidence, Confidence.NONE)
        self.assertEqual(result.measurements, ())
        self.assertEqual(result.completeness.properties_present, 0)
        self.assertIn("farmer_context", {item.name for item in result.missing})
        self.assertIn("cannot be assessed", result.summary)

    def test_context_without_soil_properties_is_insufficient(self) -> None:
        result = build(SoilProfile(soil_source="FARMER_REPORTED", sample_date=date(2026, 1, 1)))
        self.assertEqual(result.status, IndicatorStatus.INSUFFICIENT_DATA)
        self.assertEqual(result.measurements, ())
        self.assertEqual(result.period.latest_observation, date(2026, 1, 1))

    def test_missing_sampling_method_is_reported(self) -> None:
        result = build(full_profile(sampling_method=""))
        self.assertIn("sampling_method", {item.name for item in result.missing})


class SoilConfidenceTests(SimpleTestCase):
    def test_farmer_reported_is_lower_than_lab_for_same_completeness(self) -> None:
        lab = build(full_profile(soil_source="LAB_TEST"))
        reported = build(full_profile(soil_source="FARMER_REPORTED"))
        self.assertEqual(lab.confidence, Confidence.HIGH)
        self.assertEqual(reported.confidence, Confidence.MEDIUM)

    def test_unknown_provenance_is_low(self) -> None:
        result = build(full_profile(soil_source="UNKNOWN"))
        self.assertEqual(result.confidence, Confidence.LOW)

    def test_freshness_and_confidence_are_separate_fields(self) -> None:
        result = build(full_profile(sample_date=date(2024, 1, 1)))
        self.assertEqual(result.period.freshness, Freshness.STALE)
        self.assertEqual(result.confidence, Confidence.LOW)


class SoilSemanticsTests(SimpleTestCase):
    def test_no_composite_score_or_health_claim(self) -> None:
        result = build(full_profile())
        payload = result.as_dict()
        self.assertIsNone(payload["score"])
        self.assertIsNone(payload["coverage"])
        self.assertEqual(payload["completeness"]["properties_present"], 6)
        self.assertTrue(any("No composite soil-health score" in text for text in result.limitations))
        self.assertNotIn("health_score", payload)

    def test_methodology_is_identified(self) -> None:
        result = build(full_profile())
        self.assertEqual(result.methodology.id, "soil.properties.v1")
        self.assertIn("descriptive", result.methodology.threshold_source)

    def test_payload_is_json_serializable(self) -> None:
        import json

        payload = json.loads(build(full_profile()).to_json())
        self.assertEqual(payload["code"], "SOIL")
        self.assertEqual(payload["measurements"][0]["value"], "7.80")
        self.assertEqual(payload["period"]["freshness"], "FRESH")
