"""Database adapters for indicator calculations (Phase 4B).

Keeps the calculation services pure (no ORM) while reading from the existing
Phase 3 tables. These functions never call NASA and never write.

Phase 4 decision R20: no snapshot table; indicators are computed on demand.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from django.db.models import Max

from apps.earth_data.models import DatasetSource, EnvironmentalObservation, Provider
from apps.farms.models import Farm, FarmerContext

from .contract import SourceReference
from .services.soil import SoilProfile


def parameter_series(
    farm: Farm,
    parameter_code: str,
    start: date,
    end: date,
) -> dict[date, Decimal | None]:
    """Daily values for one parameter inside the window.

    Rows with ``MISSING`` quality are returned as ``None``; days without a row
    are simply absent (callers treat absent as missing, never as zero).
    """
    rows = (
        EnvironmentalObservation.objects.filter(
            farm=farm,
            source__parameter_code=parameter_code,
            observation_date__gte=start,
            observation_date__lte=end,
        )
        .order_by("observation_date")
        .values_list("observation_date", "value", "quality_status")
    )
    series: dict[date, Decimal | None] = {}
    for observation_date, value, quality_status in rows:
        series[observation_date] = (
            None
            if quality_status == EnvironmentalObservation.QualityStatus.MISSING
            else value
        )
    return series


def observed_dates(
    farm: Farm,
    parameter_codes: Iterable[str] | None = None,
    *,
    start: date | None = None,
    end: date | None = None,
) -> list[date]:
    """Dates that have at least one stored observation for the farm."""
    queryset = EnvironmentalObservation.objects.filter(farm=farm)
    if parameter_codes:
        queryset = queryset.filter(source__parameter_code__in=list(parameter_codes))
    if start is not None:
        queryset = queryset.filter(observation_date__gte=start)
    if end is not None:
        queryset = queryset.filter(observation_date__lte=end)
    return list(
        queryset.order_by("observation_date")
        .values_list("observation_date", flat=True)
        .distinct()
    )


def soil_profile_from_context(context: FarmerContext | None) -> SoilProfile | None:
    """Build the pure soil value object from an already-loaded context."""
    if context is None:
        return None
    return SoilProfile(
        soil_source=context.soil_source,
        texture_class=context.texture_class,
        ph=context.ph,
        organic_carbon_percent=context.organic_carbon_percent,
        nitrogen_ppm=context.nitrogen_ppm,
        phosphorus_ppm=context.phosphorus_ppm,
        potassium_ppm=context.potassium_ppm,
        sampling_depth_cm=context.sampling_depth_cm,
        sampling_method=context.sampling_method,
        lab_name=context.lab_name,
        sample_date=context.sample_date,
    )


def soil_profile(farm: Farm) -> SoilProfile | None:
    """Farmer-context soil fields as a pure value object (``None`` when absent)."""
    return soil_profile_from_context(FarmerContext.objects.filter(farm=farm).first())


def latest_observation_date(
    farm: Farm,
    parameter_codes: Iterable[str] | None = None,
) -> date | None:
    """Newest stored observation date for the farm (one aggregate query)."""
    queryset = EnvironmentalObservation.objects.filter(
        farm=farm,
        quality_status=EnvironmentalObservation.QualityStatus.AVAILABLE,
    )
    if parameter_codes:
        queryset = queryset.filter(source__parameter_code__in=list(parameter_codes))
    return queryset.aggregate(latest=Max("observation_date"))["latest"]


def window_series(
    farm: Farm,
    parameter_codes: Iterable[str],
    start: date,
    end: date,
) -> dict[str, dict[date, Decimal | None]]:
    """All requested parameters for a window in **one** query.

    Returns ``{parameter_code: {date: value_or_None}}``; days without a row are
    absent (callers treat absent as missing, never as zero).
    """
    codes = list(dict.fromkeys(parameter_codes))
    series: dict[str, dict[date, Decimal | None]] = {code: {} for code in codes}
    rows = (
        EnvironmentalObservation.objects.filter(
            farm=farm,
            source__parameter_code__in=codes,
            observation_date__gte=start,
            observation_date__lte=end,
        )
        .values_list("source__parameter_code", "observation_date", "value", "quality_status")
    )
    for code, observation_date, value, quality_status in rows:
        series[code][observation_date] = (
            None
            if quality_status == EnvironmentalObservation.QualityStatus.MISSING
            else value
        )
    return series


def source_reference(parameter_code: str) -> SourceReference | None:
    """Provider metadata for a parameter, taken from the Phase 3 catalogue."""
    source = DatasetSource.objects.filter(
        provider=Provider.NASA_POWER,
        parameter_code=parameter_code,
        is_active=True,
    ).first()
    if source is None:
        return None
    return _to_reference(source)


def _to_reference(source: DatasetSource) -> SourceReference:
    return SourceReference(
        provider=source.provider,
        parameter=source.parameter_code,
        units=source.units,
        product=source.product,
        data_category=source.data_category,
        native_resolution_note=source.native_resolution_note,
        time_standard=source.time_standard,
        access_date=source.access_date,
    )


def source_references(parameter_codes: Iterable[str]) -> dict[str, SourceReference]:
    """Provider metadata for several parameters in **one** query."""
    codes = list(dict.fromkeys(parameter_codes))
    rows = DatasetSource.objects.filter(
        provider=Provider.NASA_POWER,
        parameter_code__in=codes,
        is_active=True,
    )
    return {row.parameter_code: _to_reference(row) for row in rows}


__all__ = [
    "latest_observation_date",
    "observed_dates",
    "parameter_series",
    "soil_profile",
    "soil_profile_from_context",
    "source_reference",
    "source_references",
    "window_series",
]
