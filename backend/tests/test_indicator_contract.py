"""Contract, coverage, confidence and freshness tests (Phase 4B)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from apps.indicators.contract import (
    Confidence,
    Coverage,
    Freshness,
    IndicatorStatus,
    Measurement,
    Methodology,
    Period,
    SourceReference,
)
from apps.indicators.coverage import (
    GRID_CELL_CONFIDENCE_CAP,
    build_period,
    combine_coverage,
    confidence_for,
    count_days,
    coverage_from_values,
    days_in_window,
    freshness_for,
    latest_window,
)


class ConfidenceBandTests(SimpleTestCase):
    def test_bands_do_not_overlap(self) -> None:
        self.assertEqual(confidence_for(Decimal("0")), Confidence.NONE)
        self.assertEqual(confidence_for(Decimal("0.0001")), Confidence.LOW)
        self.assertEqual(confidence_for(Decimal("0.5999")), Confidence.LOW)
        self.assertEqual(confidence_for(Decimal("0.60")), Confidence.MEDIUM)
        self.assertEqual(confidence_for(Decimal("0.9499")), Confidence.MEDIUM)
        self.assertEqual(confidence_for(Decimal("0.95")), Confidence.HIGH)
        self.assertEqual(confidence_for(Decimal("1")), Confidence.HIGH)

    def test_cap_limits_confidence_for_grid_cell_sources(self) -> None:
        self.assertEqual(
            confidence_for(Decimal("1"), cap=GRID_CELL_CONFIDENCE_CAP), Confidence.MEDIUM
        )
        self.assertEqual(
            confidence_for(Decimal("0.3"), cap=GRID_CELL_CONFIDENCE_CAP), Confidence.LOW
        )

    def test_ratio_is_clamped(self) -> None:
        self.assertEqual(confidence_for(Decimal("-1")), Confidence.NONE)
        self.assertEqual(confidence_for(Decimal("2")), Confidence.HIGH)


class FreshnessTests(SimpleTestCase):
    def test_bands(self) -> None:
        self.assertEqual(freshness_for(None), Freshness.UNKNOWN)
        self.assertEqual(freshness_for(0), Freshness.FRESH)
        self.assertEqual(freshness_for(7), Freshness.FRESH)
        self.assertEqual(freshness_for(8), Freshness.RECENT)
        self.assertEqual(freshness_for(30), Freshness.RECENT)
        self.assertEqual(freshness_for(31), Freshness.STALE)
        self.assertEqual(freshness_for(900), Freshness.STALE)

    def test_build_period_exposes_age_and_freshness(self) -> None:
        period = build_period(
            start=date(2025, 6, 1),
            end=date(2025, 6, 7),
            latest_observation=date(2025, 6, 7),
            today=date(2025, 6, 20),
        )
        self.assertEqual(period.age_days, 13)
        self.assertEqual(period.freshness, Freshness.RECENT)
        self.assertEqual(
            period.as_dict(),
            {
                "start": "2025-06-01",
                "end": "2025-06-07",
                "latest_observation": "2025-06-07",
                "age_days": 13,
                "freshness": "RECENT",
            },
        )

    def test_period_without_observations_is_unknown(self) -> None:
        period = build_period(
            start=date(2025, 6, 1),
            end=date(2025, 6, 7),
            latest_observation=None,
            today=date(2025, 6, 20),
        )
        self.assertIsNone(period.age_days)
        self.assertEqual(period.freshness, Freshness.UNKNOWN)


class CoverageTests(SimpleTestCase):
    def test_counts_and_ratio(self) -> None:
        coverage = Coverage(days_expected=7, days_covered=3)
        self.assertEqual(coverage.days_missing, 4)
        self.assertEqual(coverage.ratio, Decimal("0.4286"))

    def test_ratio_with_empty_window_is_zero(self) -> None:
        self.assertEqual(Coverage(days_expected=0, days_covered=0).ratio, Decimal("0"))

    def test_coverage_only_counts_non_null_days(self) -> None:
        start = date(2025, 6, 1)
        values = {
            date(2025, 6, 1): Decimal("0"),
            date(2025, 6, 2): None,
            date(2025, 6, 3): Decimal("5"),
        }
        coverage = coverage_from_values(start, date(2025, 6, 3), values, parameter="PRECTOTCORR")
        self.assertEqual(coverage.days_expected, 3)
        self.assertEqual(coverage.days_covered, 2)
        self.assertEqual(coverage.by_parameter, {"PRECTOTCORR": 2})

    def test_multi_parameter_coverage_uses_the_weakest_parameter(self) -> None:
        coverage = combine_coverage(7, {"T2M": 7, "T2M_MAX": 5, "T2M_MIN": 6})
        self.assertEqual(coverage.days_covered, 5)
        self.assertEqual(coverage.days_missing, 2)
        self.assertEqual(coverage.by_parameter["T2M_MAX"], 5)

    def test_window_helpers_are_inclusive(self) -> None:
        start, end = date(2025, 6, 1), date(2025, 6, 7)
        self.assertEqual(count_days(start, end), 7)
        self.assertEqual(len(days_in_window(start, end)), 7)
        self.assertEqual(days_in_window(start, end)[-1], end)
        self.assertEqual(count_days(end, start), 0)

    def test_latest_window_ends_at_the_newest_observation(self) -> None:
        dates = [date(2025, 6, 1), date(2025, 6, 7), date(2025, 6, 3)]
        window = latest_window(dates, 5)
        self.assertEqual(window, (date(2025, 6, 3), date(2025, 6, 7)))
        self.assertIsNone(latest_window([], 30))


class ContractSerializationTests(SimpleTestCase):
    def _result(self):
        from apps.indicators.contract import IndicatorResult

        return IndicatorResult(
            code="WATER",
            label="Water",
            status=IndicatorStatus.PARTIAL,
            confidence=Confidence.LOW,
            period=Period(
                start=date(2025, 6, 1),
                end=date(2025, 6, 7),
                latest_observation=date(2025, 6, 7),
                age_days=459,
                freshness=Freshness.STALE,
            ),
            coverage=Coverage(days_expected=7, days_covered=3, by_parameter={"PRECTOTCORR": 3}),
            summary="Test summary",
            measurements=(
                Measurement(
                    name="precipitation_total",
                    value=Decimal("14.5"),
                    unit="mm",
                    source="NASA_POWER",
                    parameter="PRECTOTCORR",
                    product="MERRA-2",
                ),
            ),
            methodology=Methodology(id="test.v1", version="1.0.0", description="test"),
            sources=(
                SourceReference(
                    provider="NASA_POWER",
                    parameter="PRECTOTCORR",
                    units="mm/day",
                    product="MERRA-2",
                    data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
                    native_resolution_note="0.5 deg x 0.625 deg (MERRA-2 native grid)",
                    time_standard="UTC",
                    access_date=date(2026, 11, 9),
                ),
            ),
            limitations=("grid cell",),
        )

    def test_score_is_always_null(self) -> None:
        payload = self._result().as_dict()
        self.assertIsNone(payload["score"])
        self.assertIsNone(self._result().score)

    def test_decimals_are_serialized_as_strings(self) -> None:
        payload = self._result().as_dict()
        self.assertEqual(payload["measurements"][0]["value"], "14.5")
        self.assertEqual(payload["coverage"]["ratio"], "0.4286")

    def test_payload_is_json_serializable(self) -> None:
        encoded = self._result().to_json()
        parsed = json.loads(encoded)
        self.assertEqual(parsed["status"], "PARTIAL")
        self.assertEqual(parsed["confidence"], "LOW")
        self.assertEqual(parsed["period"]["freshness"], "STALE")
        self.assertEqual(parsed["sources"][0]["provider"], "NASA_POWER")
        self.assertEqual(parsed["sources"][0]["access_date"], "2026-11-09")

    def test_enums_serialize_to_their_values(self) -> None:
        payload = self._result().as_dict()
        self.assertEqual(payload["status"], "PARTIAL")
        self.assertEqual(payload["period"]["freshness"], "STALE")
