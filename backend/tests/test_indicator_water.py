"""Water indicator tests (Phase 4B) — deterministic fixtures, no network."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from apps.indicators.contract import Confidence, IndicatorStatus
from apps.indicators.services.water import (
    CONTIGUOUS,
    INTERRUPTED,
    UNKNOWN_CONTIGUITY,
    calculate_water_indicator,
    default_rainy_day_threshold_mm,
)

START = date(2025, 6, 1)
END = date(2025, 6, 7)
TODAY = date(2025, 6, 20)


def series(values: list[Decimal | None], start: date = START) -> dict[date, Decimal | None]:
    return {start + timedelta(days=index): value for index, value in enumerate(values)}


def build(values: list[Decimal | None], **kwargs):
    return calculate_water_indicator(
        precipitations=series(values),
        start=START,
        end=END,
        today=TODAY,
        **kwargs,
    )


ONE_WEEK = [Decimal("0"), Decimal("2.5"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("12.0"), Decimal("0")]


class WaterMeasurementTests(SimpleTestCase):
    def test_totals_rainy_days_and_maximum(self) -> None:
        result = build(ONE_WEEK)
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.OK)
        self.assertEqual(measurements["precipitation_total"].value, Decimal("14.5"))
        self.assertEqual(measurements["precipitation_total"].unit, "mm")
        self.assertEqual(measurements["rainy_days"].value, 2)  # 2.5 and 12.0
        self.assertEqual(measurements["max_daily_rainfall"].value, Decimal("12.0"))

    def test_dry_spell_across_contiguous_days(self) -> None:
        result = build(ONE_WEEK)
        spell = next(m for m in result.measurements if m.name == "longest_observed_dry_spell")
        self.assertEqual(spell.value, 3)  # 1, 2, 3 June (0, 0, 0) after the 2.5 mm day
        self.assertIn(CONTIGUOUS, spell.method)

    def test_threshold_is_configurable(self) -> None:
        result = build(ONE_WEEK, rainy_day_threshold_mm=Decimal("2.0"))
        measurements = {item.name: item for item in result.measurements}
        self.assertEqual(measurements["rainy_days"].value, 2)  # 2.5 and 12.0 still qualify
        result_strict = build(ONE_WEEK, rainy_day_threshold_mm=Decimal("10.0"))
        self.assertEqual(
            {item.name: item for item in result_strict.measurements}["rainy_days"].value, 1
        )

    def test_default_threshold_is_one_millimetre(self) -> None:
        self.assertEqual(default_rainy_day_threshold_mm(), Decimal("1.0"))
        result = build([Decimal("0.9"), Decimal("1.0")] + [None] * 5)
        rainy = {item.name: item for item in result.measurements}["rainy_days"]
        self.assertEqual(rainy.value, 1)  # 0.9 excluded, 1.0 included


class WaterMissingDataTests(SimpleTestCase):
    def test_missing_days_are_not_treated_as_zero_rainfall(self) -> None:
        values = [Decimal("5"), Decimal("5"), None, None, None, None, None]
        result = build(values)
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.PARTIAL)
        self.assertEqual(measurements["precipitation_total"].value, Decimal("10"))
        self.assertEqual(result.coverage.days_covered, 2)
        self.assertEqual(result.coverage.days_missing, 5)
        self.assertIn("observed total", result.summary)
        self.assertIn("not a complete-window total", result.summary)

    def test_dry_spell_is_interrupted_by_missing_days(self) -> None:
        values = [
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            None,  # gap
            Decimal("0"),
            Decimal("0"),
            Decimal("2.0"),
        ]
        result = build(values)
        spell = next(m for m in result.measurements if m.name == "longest_observed_dry_spell")

        self.assertEqual(spell.value, 3)
        self.assertIn(INTERRUPTED, spell.method)
        self.assertTrue(any("interrupt the dry-spell search" in text for text in result.limitations))
        self.assertIn("missing days", result.summary)

    def test_all_missing_returns_insufficient_data(self) -> None:
        result = build([None] * 7)
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.INSUFFICIENT_DATA)
        self.assertEqual(result.confidence, Confidence.NONE)
        self.assertIsNone(measurements["precipitation_total"].value)
        self.assertIsNone(measurements["rainy_days"].value)
        self.assertIsNone(measurements["longest_observed_dry_spell"].value)
        self.assertEqual(
            next(m for m in result.measurements if m.name == "longest_observed_dry_spell").method,
            f"longest run of covered days below 1.0 mm/day; contiguity={UNKNOWN_CONTIGUITY}",
        )
        self.assertIn("cannot be assessed", result.summary)

    def test_empty_window(self) -> None:
        result = calculate_water_indicator(
            precipitations={},
            start=START,
            end=date(2025, 5, 31),  # inverted window -> zero expected days
            today=TODAY,
        )
        self.assertEqual(result.coverage.days_expected, 0)
        self.assertEqual(result.status, IndicatorStatus.INSUFFICIENT_DATA)
        self.assertIsNone(result.period.latest_observation)


class WaterCoverageAndConfidenceTests(SimpleTestCase):
    def test_coverage_bands_drive_confidence_and_status(self) -> None:
        cases = [
            (0, IndicatorStatus.INSUFFICIENT_DATA, Confidence.NONE),
            (2, IndicatorStatus.PARTIAL, Confidence.LOW),    # 28.6%
            (5, IndicatorStatus.PARTIAL, Confidence.MEDIUM),  # 71.4%
            (7, IndicatorStatus.OK, Confidence.MEDIUM),       # 100%, capped for grid data
        ]
        for covered, expected_status, expected_confidence in cases:
            with self.subTest(covered=covered):
                values = [Decimal("0")] * covered + [None] * (7 - covered)
                result = build(values)
                self.assertEqual(result.status, expected_status)
                self.assertEqual(result.confidence, expected_confidence)
                self.assertEqual(result.coverage.days_covered, covered)
                self.assertEqual(result.coverage.days_expected, 7)

    def test_grid_cell_confidence_is_capped_below_high(self) -> None:
        result = build(ONE_WEEK)
        self.assertEqual(result.coverage.ratio, Decimal("1.0000"))
        self.assertNotEqual(result.confidence, Confidence.HIGH)
        self.assertEqual(result.confidence, Confidence.MEDIUM)


class WaterFreshnessAndProvenanceTests(SimpleTestCase):
    def test_stale_window_is_labelled(self) -> None:
        result = build(ONE_WEEK)
        self.assertEqual(result.period.latest_observation, END)
        self.assertEqual(result.period.age_days, 13)
        self.assertEqual(result.period.freshness.value, "RECENT")

        stale = calculate_water_indicator(
            precipitations=series(ONE_WEEK),
            start=START,
            end=END,
            today=date(2026, 11, 9),
        )
        self.assertEqual(stale.period.freshness.value, "STALE")
        self.assertGreater(stale.period.age_days, 365)

    def test_source_reference_is_preserved(self) -> None:
        from apps.indicators.contract import SourceReference

        source = SourceReference(
            provider="NASA_POWER",
            parameter="PRECTOTCORR",
            units="mm/day",
            product="MERRA-2",
            data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
            native_resolution_note="0.5 deg x 0.625 deg (MERRA-2 native grid)",
            time_standard="UTC",
            access_date=date(2026, 11, 9),
        )
        result = build(ONE_WEEK, source=source)
        payload = result.as_dict()

        self.assertEqual(payload["sources"][0]["provider"], "NASA_POWER")
        self.assertEqual(payload["sources"][0]["units"], "mm/day")
        self.assertEqual(payload["sources"][0]["product"], "MERRA-2")
        self.assertTrue(all(m.source == "NASA_POWER" for m in result.measurements))
        self.assertTrue(all(m.unit == "mm" for m in result.measurements[:1]))

    def test_irrigation_context_is_reported_not_scored(self) -> None:
        from apps.indicators.contract import Measurement

        context = (
            Measurement(
                name="irrigation_available",
                value=1,
                unit="boolean",
                quality="FARMER_REPORTED",
                method="farmer-entered",
            ),
        )
        result = build(ONE_WEEK, irrigation_context=context)
        self.assertEqual(result.context[0].quality, "FARMER_REPORTED")
        self.assertIsNone(result.score)

    def test_methodology_and_limitations_are_explicit(self) -> None:
        result = build(ONE_WEEK)
        self.assertEqual(result.methodology.id, "water.rainfall.v1")
        self.assertTrue(any("grid-cell" in text for text in result.limitations))
        self.assertTrue(any("latest available observation" in text for text in result.limitations))
        missing_names = {item.name for item in result.missing}
        self.assertEqual(
            missing_names,
            {"soil_moisture", "reference_evapotranspiration", "irrigation_records"},
        )
