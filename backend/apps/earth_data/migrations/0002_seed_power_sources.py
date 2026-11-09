"""Seed the NASA POWER parameter catalogue (Phase 3C).

Data source: the Phase 3A audit, verified against the live API on 2026-11-09
(POWER Daily API v2.10.3). Values are inlined rather than imported so this
migration keeps producing the same rows even if the provider module changes.

Idempotent: rows are matched on the natural key, so re-running is safe and a
manually edited row is not overwritten.
"""

from django.db import migrations

ACCESS_DATE = "2026-11-09"
DOCS_URL = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"
ATTRIBUTION = "NASA POWER (NASA Langley Research Center)"
MERRA2_RESOLUTION = "0.5 deg x 0.625 deg (MERRA-2 native grid)"

# (parameter_code, units, long_name, product, data_category, daily_aggregation,
#  first_available_date, native_resolution_note)
CATALOGUE = (
    (
        "T2M",
        "C",
        "Temperature at 2 Meters",
        "MERRA-2",
        "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        "MEAN",
        "1981-01-01",
        MERRA2_RESOLUTION,
    ),
    (
        "T2M_MAX",
        "C",
        "Temperature at 2 Meters Maximum",
        "MERRA-2",
        "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        "MAXIMUM",
        "1981-01-01",
        MERRA2_RESOLUTION,
    ),
    (
        "T2M_MIN",
        "C",
        "Temperature at 2 Meters Minimum",
        "MERRA-2",
        "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        "MINIMUM",
        "1981-01-01",
        MERRA2_RESOLUTION,
    ),
    (
        "PRECTOTCORR",
        "mm/day",
        "Precipitation Corrected",
        "MERRA-2",
        "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        "TOTAL",
        "1981-01-01",
        MERRA2_RESOLUTION,
    ),
    (
        "RH2M",
        "%",
        "Relative Humidity at 2 Meters",
        "MERRA-2",
        "DERIVED",
        "MEAN",
        "1981-01-01",
        MERRA2_RESOLUTION,
    ),
    (
        "WS2M",
        "m/s",
        "Wind Speed at 2 Meters",
        "MERRA-2",
        "DERIVED",
        "MEAN",
        "1981-01-01",
        MERRA2_RESOLUTION,
    ),
    (
        "ALLSKY_SFC_SW_DWN",
        "MJ/m^2/day",
        "All Sky Surface Shortwave Downward Irradiance",
        "CERES SYN1deg",
        "SATELLITE_DERIVED_ESTIMATE",
        "TOTAL",
        "1984-01-01",
        # Native resolution of CERES SYN1deg has not been re-verified, so it is
        # deliberately left blank rather than asserting an unconfirmed value.
        "",
    ),
)


def seed_catalogue(apps, schema_editor):
    DatasetSource = apps.get_model("earth_data", "DatasetSource")
    for (
        code,
        units,
        long_name,
        product,
        data_category,
        aggregation,
        first_available,
        resolution_note,
    ) in CATALOGUE:
        DatasetSource.objects.get_or_create(
            provider="NASA_POWER",
            parameter_code=code,
            community="AG",
            time_standard="UTC",
            defaults={
                "product": product,
                "long_name": long_name,
                "units": units,
                "temporal_resolution": "DAILY",
                "data_category": data_category,
                "daily_aggregation": aggregation,
                "native_resolution_note": resolution_note,
                "first_available_date": first_available,
                "attribution": ATTRIBUTION,
                "docs_url": DOCS_URL,
                "access_date": ACCESS_DATE,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("earth_data", "0001_initial"),
    ]

    operations = [
        # Reverse is intentionally a no-op: deleting catalogue rows could break
        # the PROTECT relationship from existing observations.
        migrations.RunPython(seed_catalogue, migrations.RunPython.noop),
    ]
