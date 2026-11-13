"""Heat indicator tests (Phase 4B) — deterministic fixtures, no network."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.test import SimpleTestCase

from apps.indicators.contract import Confidence, IndicatorStatus, SourceReference
from apps.indicators.services.heat import calculate_heat_indicator

START = date(2025, 6, 1)
END = date(2025, 6, 7)
TODAY = date(2025, 6, 20)

MEANS = [Decimal("20"), Decimal("21"), Decimal("22"), Decimal("23"), Decimal("24"), Decimal("25"), Decimal("26")]
MAXIMA = [Decimal("34"), Decimal("35"), Decimal("36"), Decimal("39"), Decimal("40"), Decimal("41"), Decimal("30")]
MINIMA = [Decimal("4"), Decimal("5"), Decimal("6"), Decimal("7"), Decimal("8"), Decimal("9"), Decimal("10")]


def series(values: list[Decimal | None]) -> dict[date, Decimal | None]:
    return {START + timedelta(days=index): value for index, value in enumerate(values)}


def build(
    means=MEANS,
    maxima=MAXIMA,
    minima=MINIMA,
    **kwargs,
):
    return calculate_heat_indicator(
        mean_temperatures=series(means),
        max_temperatures=series(maxima),
        min_temperatures=series(minima),
        start=START,
        end=END,
        today=TODAY,
        **kwargs,
    )


class HeatMeasurementTests(SimpleTestCase):
    def test_means_are_decimal_safe(self) -> None:
        result = build()
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.OK)
        self.assertEqual(measurements["mean_temperature"].value, Decimal("23.0000"))
        # (34+35+36+39+40+41+30) / 7 = 36.4286
        self.assertEqual(measurements["mean_daily_maximum"].value, Decimal("36.4286"))
        self.assertEqual(measurements["mean_daily_minimum"].value, Decimal("7.0000"))
        self.assertEqual(measurements["mean_temperature"].unit, "C")

    def test_exposure_counts_use_approved_thresholds(self) -> None:
        result = build()
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(measurements["hot_days"].value, 5)       # 35, 36, 39, 40, 41
        self.assertEqual(measurements["very_hot_days"].value, 2)  # 40, 41
        self.assertEqual(measurements["cool_nights"].value, 2)    # 4, 5
        self.assertIn("35", measurements["hot_days"].method)
        self.assertIn("40", measurements["very_hot_days"].method)
        self.assertIn("5", measurements["cool_nights"].method)

    def test_thresholds_are_configurable(self) -> None:
        result = build(hot_day_c=Decimal("38"), very_hot_day_c=Decimal("45"), cool_night_c=Decimal("4"))
        measurements = {item.name: item for item in result.measurements}
        self.assertEqual(measurements["hot_days"].value, 3)      # 39, 40, 41
        self.assertEqual(measurements["very_hot_days"].value, 0)  # none >= 45
        self.assertEqual(measurements["cool_nights"].value, 1)   # 4 only

    def test_boundary_values_are_inclusive(self) -> None:
        result = build(
            means=[Decimal("20")] * 7,
            maxima=[Decimal("35"), Decimal("39.9"), Decimal("40"), Decimal("34.9"), Decimal("0"), Decimal("0"), Decimal("0")],
            minima=[Decimal("5"), Decimal("5.1"), Decimal("4.9"), Decimal("10"), Decimal("10"), Decimal("10"), Decimal("10")],
        )
        measurements = {item.name: item for item in result.measurements}
        self.assertEqual(measurements["hot_days"].value, 3)      # 35, 39.9, 40
        self.assertEqual(measurements["very_hot_days"].value, 1)  # 40
        self.assertEqual(measurements["cool_nights"].value, 2)   # 5 and 4.9


class HeatMissingDataTests(SimpleTestCase):
    def test_missing_temperature_is_not_zero(self) -> None:
        result = build(
            means=[Decimal("20"), None, Decimal("22"), None, None, None, None],
            maxima=[Decimal("30"), None, Decimal("36"), None, None, None, None],
            minima=[Decimal("10"), None, Decimal("12"), None, None, None, None],
        )
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.PARTIAL)
        self.assertEqual(result.coverage.days_covered, 2)
        self.assertEqual(result.coverage.days_missing, 5)
        self.assertEqual(measurements["mean_temperature"].value, Decimal("21.0000"))
        self.assertEqual(measurements["hot_days"].value, 1)  # only 36 >= 35
        self.assertEqual(measurements["cool_nights"].value, 0)
        self.assertIn("observed days only", " ".join(result.limitations))

    def test_unobserved_parameter_reports_null_counts_not_zero(self) -> None:
        result = build(
            means=MEANS,
            maxima=[None] * 7,   # T2M_MAX entirely missing
            minima=MINIMA,
        )
        measurements = {item.name: item for item in result.measurements}

        self.assertEqual(result.status, IndicatorStatus.PARTIAL)
        self.assertIsNone(measurements["mean_daily_maximum"].value)
        self.assertIsNone(measurements["hot_days"].value)
        self.assertIsNone(measurements["very_hot_days"].value)
        self.assertEqual(measurements["cool_nights"].value, 2)
        self.assertEqual(result.coverage.by_parameter["T2M_MAX"], 0)
        self.assertIn("daily maximum temperature unavailable", result.summary)

    def test_all_parameters_missing_returns_insufficient_data(self) -> None:
        result = build(maxima=[None] * 7, means=[None] * 7, minima=[None] * 7)
        self.assertEqual(result.status, IndicatorStatus.INSUFFICIENT_DATA)
        self.assertEqual(result.confidence, Confidence.NONE)
        self.assertIsNone(result.period.latest_observation)
        self.assertIn("cannot be assessed", result.summary)

    def test_empty_window(self) -> None:
        result = calculate_heat_indicator(
            mean_temperatures={},
            max_temperatures={},
            min_temperatures={},
            start=START,
            end=date(2025, 5, 31),
            today=TODAY,
        )
        self.assertEqual(result.coverage.days_expected, 0)
        self.assertEqual(result.status, IndicatorStatus.INSUFFICIENT_DATA)


class HeatCoverageAndConfidenceTests(SimpleTestCase):
    def test_coverage_is_the_weakest_parameter(self) -> None:
        result = build(
            means=MEANS,
            maxima=[Decimal("30")] * 5 + [None] * 2,
            minima=MINIMA,  # 7 days
        )
        self.assertEqual(result.coverage.days_expected, 7)
        self.assertEqual(result.coverage.days_covered, 5)
        self.assertEqual(
            result.coverage.by_parameter,
            {"T2M": 7, "T2M_MAX": 5, "T2M_MIN": 7},
        )
        self.assertEqual(result.confidence, Confidence.MEDIUM)  # 71.4%

    def test_partial_coverage_is_low_confidence(self) -> None:
        result = build(
            means=[Decimal("20")] * 2 + [None] * 5,
            maxima=[Decimal("30")] * 2 + [None] * 5,
            minima=[Decimal("10")] * 2 + [None] * 5,
        )
        self.assertEqual(result.coverage.ratio, Decimal("0.2857"))
        self.assertEqual(result.confidence, Confidence.LOW)
        self.assertEqual(result.status, IndicatorStatus.PARTIAL)

    def test_full_coverage_is_capped_at_medium_for_grid_cells(self) -> None:
        result = build()
        self.assertEqual(result.coverage.ratio, Decimal("1.0000"))
        self.assertEqual(result.confidence, Confidence.MEDIUM)

    def test_coverage_is_not_overestimated_when_parameters_use_different_dates(self) -> None:
        """Required parameters on incompatible dates must not be treated as complete."""
        result = calculate_heat_indicator(
            mean_temperatures=series([Decimal("20")] * 7),
            max_temperatures={
                START: Decimal("34"),
                START + timedelta(days=1): Decimal("36"),
            },
            min_temperatures={
                START + timedelta(days=5): Decimal("8"),
                START + timedelta(days=6): Decimal("9"),
            },
            start=START,
            end=END,
            today=TODAY,
        )

        self.assertEqual(
            result.coverage.by_parameter, {"T2M": 7, "T2M_MAX": 2, "T2M_MIN": 2}
        )
        # Headline coverage is the weakest parameter, never the union of dates.
        self.assertEqual(result.coverage.days_covered, 2)
        self.assertEqual(result.coverage.days_missing, 5)
        self.assertEqual(result.status, IndicatorStatus.PARTIAL)
        self.assertEqual(result.confidence, Confidence.LOW)


class HeatSemanticsAndProvenanceTests(SimpleTestCase):
    def test_cool_nights_are_not_described_as_frost(self) -> None:
        result = build()
        cool = next(m for m in result.measurements if m.name == "cool_nights")
        self.assertIn("not a frost indicator", cool.method)
        self.assertTrue(any("not evidence of frost" in text for text in result.limitations))

    def test_no_crop_stress_claims(self) -> None:
        result = build()
        self.assertTrue(
            any("not universal agricultural or crop-stress thresholds" in text for text in result.limitations)
        )
        missing_names = {item.name for item in result.missing}
        self.assertEqual(missing_names, {"crop_heat_thresholds", "growth_stage"})
        self.assertIsNone(result.score)

    def test_sources_are_preserved_per_parameter(self) -> None:
        refs = {
            code: SourceReference(
                provider="NASA_POWER",
                parameter=code,
                units="C",
                product="MERRA-2",
                data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
                native_resolution_note="0.5 deg x 0.625 deg (MERRA-2 native grid)",
                time_standard="UTC",
                access_date=date(2026, 11, 9),
            )
            for code in ("T2M", "T2M_MAX", "T2M_MIN")
        }
        result = build(sources=refs)
        payload = result.as_dict()

        self.assertEqual({item["parameter"] for item in payload["sources"]}, {"T2M", "T2M_MAX", "T2M_MIN"})
        by_parameter = {m.parameter: m for m in result.measurements}
        self.assertEqual(by_parameter["T2M"].product, "MERRA-2")
        self.assertEqual(by_parameter["T2M_MAX"].source, "NASA_POWER")

    def test_freshness_is_reported_separately_from_confidence(self) -> None:
        result = build()
        self.assertEqual(result.period.latest_observation, END)
        self.assertEqual(result.period.freshness.value, "RECENT")
        self.assertEqual(result.confidence, Confidence.MEDIUM)
