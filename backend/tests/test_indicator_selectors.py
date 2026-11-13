"""Indicator DB adapters and end-to-end service smoke tests (Phase 4B).

Uses the real Phase 3 tables (EnvironmentalObservation / DatasetSource) with the
existing persistence fixtures; no network calls.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.earth_data.models import DatasetSource, EnvironmentalObservation
from apps.farms.models import FarmerContext
from apps.earth_data.services import persist_power_response, start_fetch_job
from apps.indicators.contract import IndicatorStatus
from apps.indicators.selectors import (
    latest_observation_date,
    observed_dates,
    parameter_series,
    soil_profile,
    source_reference,
    source_references,
)
from apps.indicators.services.heat import calculate_heat_indicator
from apps.indicators.services.soil import calculate_soil_indicator
from apps.indicators.services.water import calculate_water_indicator
from tests.test_earth_data_persistence import DATES, build_response, make_farm


class SelectorTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm("Indicator Farm", "indicator_farmer")
        response = build_response()
        persist_power_response(start_fetch_job(farm=self.farm, query=response.query), response)

    def test_parameter_series_returns_daily_decimals(self) -> None:
        series = parameter_series(self.farm, "T2M", DATES[0], DATES[-1])
        self.assertEqual(len(series), 7)
        self.assertEqual(series[DATES[0]], Decimal("16.1500"))

    def test_missing_quality_is_returned_as_none(self) -> None:
        farm = make_farm("Missing Farm", "missing_farmer")
        response = build_response({"T2M": {"20240103": -999.0}})
        persist_power_response(start_fetch_job(farm=farm, query=response.query), response)

        series = parameter_series(farm, "T2M", DATES[0], DATES[-1])
        self.assertIsNone(series[date(2024, 1, 3)])
        self.assertIsNotNone(series[date(2024, 1, 2)])

    def test_series_is_farm_scoped(self) -> None:
        other = make_farm("Other Indicator Farm", "other_farmer")
        self.assertEqual(parameter_series(other, "T2M", DATES[0], DATES[-1]), {})

    def test_observed_dates(self) -> None:
        self.assertEqual(observed_dates(self.farm, ["T2M"]), DATES)
        self.assertEqual(observed_dates(self.farm, ["UNKNOWN_CODE"]), [])

    def test_latest_observation_date_ignores_missing_quality_rows(self) -> None:
        """A later MISSING row is not an observation and must not advance the window."""
        source = DatasetSource.objects.get(
            provider="NASA_POWER", parameter_code="PRECTOTCORR", is_active=True
        )
        EnvironmentalObservation.objects.create(
            farm=self.farm,
            source=source,
            observation_date=date(2024, 1, 10),
            value=None,
            quality_status=EnvironmentalObservation.QualityStatus.MISSING,
            requested_longitude=Decimal("30.95"),
            requested_latitude=Decimal("30.79"),
        )

        self.assertEqual(latest_observation_date(self.farm), DATES[-1])
        self.assertEqual(latest_observation_date(self.farm, ["PRECTOTCORR"]), DATES[-1])

    def test_latest_observation_date_is_farm_scoped(self) -> None:
        other = make_farm("Latest Other Farm", "latest_other_farmer")
        self.assertIsNone(latest_observation_date(other))

    def test_source_reference_matches_the_catalogue(self) -> None:
        reference = source_reference("PRECTOTCORR")
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual(reference.provider, "NASA_POWER")
        self.assertEqual(reference.units, "mm/day")
        self.assertEqual(reference.product, "MERRA-2")
        self.assertEqual(reference.time_standard, "UTC")
        self.assertEqual(reference.access_date, date(2026, 11, 9))
        self.assertIn("MERRA-2 native grid", reference.native_resolution_note)

    def test_source_reference_for_unknown_parameter_is_none(self) -> None:
        self.assertIsNone(source_reference("NOT_A_PARAMETER"))

    def test_source_references_bundles_heat_parameters(self) -> None:
        refs = source_references(["T2M", "T2M_MAX", "T2M_MIN", "T2M"])
        self.assertEqual(set(refs), {"T2M", "T2M_MAX", "T2M_MIN"})
        self.assertEqual(refs["T2M_MAX"].units, "C")

    def test_inactive_catalogue_row_is_ignored(self) -> None:
        DatasetSource.objects.filter(parameter_code="WS2M").update(is_active=False)
        self.assertIsNone(source_reference("WS2M"))


class ServiceOverStoredDataTests(TestCase):
    """The services work on real stored rows via the selectors."""

    def setUp(self) -> None:
        self.farm = make_farm("Stored Farm", "stored_farmer")
        response = build_response()
        persist_power_response(start_fetch_job(farm=self.farm, query=response.query), response)

    def test_water_indicator_from_stored_observations(self) -> None:
        precipitations = parameter_series(self.farm, "PRECTOTCORR", DATES[0], DATES[-1])
        result = calculate_water_indicator(
            precipitations=precipitations,
            start=DATES[0],
            end=DATES[-1],
            today=date(2024, 1, 10),
            source=source_reference("PRECTOTCORR"),
        )

        self.assertEqual(result.status, IndicatorStatus.OK)
        measurements = {item.name: item for item in result.measurements}
        # Fixture: 0, 0, 0, 0, 0.08, 0.01, 0.42 mm
        self.assertEqual(measurements["precipitation_total"].value, Decimal("0.51"))
        self.assertEqual(measurements["rainy_days"].value, 0)  # all below 1 mm
        self.assertEqual(measurements["longest_observed_dry_spell"].value, 7)
        self.assertEqual(result.sources[0].parameter, "PRECTOTCORR")

    def test_heat_indicator_from_stored_observations(self) -> None:
        result = calculate_heat_indicator(
            mean_temperatures=parameter_series(self.farm, "T2M", DATES[0], DATES[-1]),
            max_temperatures=parameter_series(self.farm, "T2M_MAX", DATES[0], DATES[-1]),
            min_temperatures=parameter_series(self.farm, "T2M_MIN", DATES[0], DATES[-1]),
            start=DATES[0],
            end=DATES[-1],
            today=date(2024, 1, 10),
            sources=source_references(["T2M", "T2M_MAX", "T2M_MIN"]),
        )

        self.assertEqual(result.status, IndicatorStatus.OK)
        measurements = {item.name: item for item in result.measurements}
        self.assertEqual(measurements["hot_days"].value, 0)       # January maxima <= 24.58 °C
        self.assertEqual(measurements["very_hot_days"].value, 0)
        self.assertEqual(measurements["cool_nights"].value, 0)    # minima >= 9.9 °C
        self.assertEqual(len(result.sources), 3)
        self.assertIsNone(result.score)


class SoilSelectorTests(TestCase):
    def setUp(self) -> None:
        self.farm = make_farm("Soil Farm", "soil_farmer")

    def test_soil_profile_reads_farmer_context(self) -> None:
        FarmerContext.objects.create(
            farm=self.farm,
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

        profile = soil_profile(self.farm)
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.soil_source, "LAB_TEST")
        self.assertEqual(profile.ph, Decimal("7.80"))
        self.assertEqual(profile.texture_class, "clay_loam")
        self.assertEqual(profile.sample_date, date(2026, 3, 15))
        self.assertEqual(profile.sampling_depth_cm, 30)

    def test_soil_profile_is_none_without_context(self) -> None:
        self.assertIsNone(soil_profile(self.farm))

    def test_soil_indicator_from_stored_context(self) -> None:
        FarmerContext.objects.create(
            farm=self.farm,
            soil_source="LAB_TEST",
            texture_class="clay_loam",
            ph=Decimal("7.80"),
            sample_date=date(2026, 3, 15),
        )
        profile = soil_profile(self.farm)
        result = calculate_soil_indicator(profile=profile, today=date(2026, 11, 9))

        self.assertEqual(result.status, IndicatorStatus.PARTIAL)  # only 2 of 6 properties
        self.assertEqual(result.completeness.properties_present, 2)
        self.assertEqual(result.period.freshness.value, "FRESH")
        self.assertIsNone(result.score)
        self.assertEqual({m.name for m in result.measurements}, {"ph", "texture_class"})
