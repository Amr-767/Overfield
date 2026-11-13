"""Market indicator tests (Phase 4C) — must stay honestly UNAVAILABLE."""

from __future__ import annotations

import json
from datetime import date

from django.test import SimpleTestCase

from apps.indicators.contract import Confidence, Freshness, IndicatorStatus
from apps.indicators.services.market import (
    MARKET_METHODOLOGY,
    NATIONAL_SOURCES_NOTE,
    calculate_market_indicator,
)

START = date(2025, 6, 1)
END = date(2025, 6, 30)
TODAY = date(2026, 11, 9)


def build(**kwargs):
    return calculate_market_indicator(start=START, end=END, today=TODAY, **kwargs)


class MarketStatusTests(SimpleTestCase):
    def test_market_is_unavailable(self) -> None:
        result = build(region_code="EG-GH", country_code="EG")
        self.assertEqual(result.status, IndicatorStatus.UNAVAILABLE)
        self.assertEqual(result.confidence, Confidence.NONE)
        self.assertIsNone(result.score)
        self.assertEqual(result.measurements, ())
        self.assertEqual(result.sources, ())
        self.assertIsNone(result.coverage)
        self.assertIsNone(result.completeness)

    def test_no_prices_are_invented(self) -> None:
        payload = build(region_code="EG-GH").as_dict()
        self.assertEqual(payload["measurements"], [])
        self.assertNotIn("price", json.dumps(payload["measurements"]))
        self.assertIn("No price is estimated or invented", payload["summary"])

    def test_region_is_named_in_the_summary(self) -> None:
        result = build(region_code="EG-GH", country_code="EG")
        self.assertIn("EG-GH", result.summary)
        self.assertIn("(EG)", result.summary)

    def test_missing_inputs_are_explicit(self) -> None:
        result = build(region_code="EG-GH")
        names = {item.name for item in result.missing}
        self.assertEqual(
            names,
            {"local_market_prices", "crop_specific_price", "market_access", "expected_yield"},
        )

    def test_limitations_reference_national_sources_as_context_only(self) -> None:
        result = build(region_code="EG-GH")
        self.assertIn(NATIONAL_SOURCES_NOTE, result.limitations)
        self.assertTrue(any("not represent a local agricultural market" in text for text in result.limitations))
        self.assertTrue(any("No synthetic" in text for text in result.limitations))

    def test_market_has_no_climate_observation_period(self) -> None:
        result = build(region_code="EG-GH")
        self.assertIsNone(result.period)
        payload = result.as_dict()
        self.assertIsNone(payload["period"])
        self.assertIsNone(payload["as_of"])
        self.assertEqual(result.status, IndicatorStatus.UNAVAILABLE)

    def test_methodology_is_identified(self) -> None:
        result = build(region_code="EG-GH")
        self.assertEqual(result.methodology.id, MARKET_METHODOLOGY.id)
        self.assertEqual(result.methodology.id, "market.unavailable.v1")

    def test_payload_is_json_serializable(self) -> None:
        payload = json.loads(build(region_code="EG-GH").to_json())
        self.assertEqual(payload["code"], "MARKET")
        self.assertEqual(payload["status"], "UNAVAILABLE")
        self.assertIsNone(payload["score"])
        self.assertEqual(payload["measurements"], [])
