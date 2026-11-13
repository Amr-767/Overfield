"""Market indicator (Phase 4C).

Approved decision R18: the MARKET indicator is **UNAVAILABLE** in this phase.

There is no verified local farm-gate price source for the demonstration region,
and national series must not be presented as local market prices. This service
therefore returns no measurements and no synthetic prices; it documents the
verified national sources as *context only* and lists what is missing.

Verified national sources (2026-11-09, see DATA_PROVENANCE.md):
* FAOSTAT producer prices (Egypt, annual, LCU/SLC/USD per tonne);
* WFP Egypt food prices (national/urban retail, EGP per consumer unit).
Both are national aggregates and are **not** used to compute anything here.
"""

from __future__ import annotations

from datetime import date

from ..contract import (
    Confidence,
    Driver,
    DriverDirection,
    Freshness,
    IndicatorResult,
    IndicatorStatus,
    Methodology,
    MissingInput,
    Period,
)

MARKET_METHODOLOGY = Methodology(
    id="market.unavailable.v1",
    version="1.0.0",
    description=(
        "Market value is not assessed: no verified local farm-gate price source exists for the "
        "demonstration region. National reference series are documented as context only."
    ),
    threshold_source="No price thresholds or scoring are defined (decision R18).",
)

NATIONAL_SOURCES_NOTE = (
    "National reference series exist but are not local farm-gate prices: FAOSTAT producer prices "
    "(Egypt, annual, per tonne) and WFP Egypt food prices (national/urban retail, EGP per consumer "
    "unit). They are documented in DATA_PROVENANCE.md and are not used in this indicator."
)


def calculate_market_indicator(
    *,
    start: date,
    end: date,
    today: date,
    region_code: str = "",
    country_code: str = "",
) -> IndicatorResult:
    """Return the honest UNAVAILABLE market indicator for a farm."""
    region = region_code.strip() or "the farm's region"
    country = f" ({country_code.strip()})" if country_code.strip() else ""

    return IndicatorResult(
        code="MARKET",
        label="Market",
        status=IndicatorStatus.UNAVAILABLE,
        confidence=Confidence.NONE,
        # Market is unavailable and has no observation period; do not attach
        # the climate window passed by the summary orchestrator.
        period=None,
        coverage=None,
        summary=(
            f"No verified local market price source is available for {region}{country}, so market "
            "value cannot be assessed. No price is estimated or invented."
        ),
        measurements=(),
        context=(),
        drivers=(
            Driver(
                name="Local market price source",
                direction=DriverDirection.NEUTRAL,
                value="unavailable",
            ),
        ),
        missing=(
            MissingInput(
                name="local_market_prices",
                impact="No local farm-gate or wholesale price series is available for this region.",
                required_for="market value",
            ),
            MissingInput(
                name="crop_specific_price",
                impact="Prices cannot be matched to the farm's crops without a local source.",
                required_for="market value",
            ),
            MissingInput(
                name="market_access",
                impact="Distance, transport cost and buyer access are not recorded.",
                required_for="market opportunity",
            ),
            MissingInput(
                name="expected_yield",
                impact="Revenue cannot be estimated without a locally appropriate yield reference.",
                required_for="market value",
            ),
        ),
        methodology=MARKET_METHODOLOGY,
        sources=(),
        limitations=(
            "No synthetic, demo or manually curated prices are used (decision R18).",
            NATIONAL_SOURCES_NOTE,
            "National averages do not represent a local agricultural market.",
            "No market trend is inferred.",
        ),
    )


__all__ = ["MARKET_METHODOLOGY", "NATIONAL_SOURCES_NOTE", "calculate_market_indicator"]
