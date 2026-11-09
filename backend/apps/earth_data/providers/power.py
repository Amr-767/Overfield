"""NASA POWER Daily Point API client (Phase 3B).

Design goals
------------
* Only parameter codes verified in the Phase 3A audit are accepted.
* The request is always ``community=AG``, ``format=JSON`` and
  ``time-standard=UTC``; the returned time standard is asserted, not assumed.
* HTTP communication lives in :mod:`power_transport`; parsing here is a pure
  function so it can be unit-tested without any network.
* Failures become typed exceptions (:mod:`apps.earth_data.exceptions`).
* Missing values (POWER fill ``-999.0``) become ``None``, never a fake number.
* Identical queries are served from a short-lived in-process cache to avoid
  hammering POWER (the docs warn that repeated identical requests can block).

Official references (accessed 2026-11-09):
* https://power.larc.nasa.gov/docs/services/api/temporal/daily/
* https://power.larc.nasa.gov/docs/faqss/  (see DATA_PROVENANCE.md)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence
from urllib.parse import urlencode

from ..exceptions import (
    PowerConfigurationError,
    PowerError,
    PowerRequestError,
    PowerResponseError,
    PowerTransientError,
)
from .power_transport import HttpPowerTransport, PowerTransport, RawResponse

logger = logging.getLogger(__name__)

DAILY_POINT_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
COMMUNITY_AGROCLIMATOLOGY = "AG"
TIME_STANDARD_UTC = "UTC"
RESPONSE_FORMAT_JSON = "JSON"

MINIMUM_SERVICE_DATE = date(1981, 1, 1)
DEFAULT_FILL_VALUE = -999.0
MAX_PARAMETERS_PER_REQUEST = 20
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

DailyAggregation = Literal["MEAN", "MAXIMUM", "MINIMUM", "TOTAL"]
DataCategory = Literal[
    "REANALYSIS_OR_ASSIMILATION_ESTIMATE",
    "SATELLITE_DERIVED_ESTIMATE",
    "DERIVED",
]


@dataclass(frozen=True, slots=True)
class PowerParameter:
    """One verified POWER parameter (units and semantics from the audit)."""

    code: str
    units: str
    long_name: str
    product: str
    data_category: DataCategory
    daily_aggregation: DailyAggregation
    first_available_date: date = MINIMUM_SERVICE_DATE


#: Only these codes were verified against the live API in Phase 3A.
POWER_PARAMETERS: Mapping[str, PowerParameter] = {
    "T2M": PowerParameter(
        code="T2M",
        units="C",
        long_name="Temperature at 2 Meters",
        product="MERRA-2",
        data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        daily_aggregation="MEAN",
    ),
    "T2M_MAX": PowerParameter(
        code="T2M_MAX",
        units="C",
        long_name="Temperature at 2 Meters Maximum",
        product="MERRA-2",
        data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        daily_aggregation="MAXIMUM",
    ),
    "T2M_MIN": PowerParameter(
        code="T2M_MIN",
        units="C",
        long_name="Temperature at 2 Meters Minimum",
        product="MERRA-2",
        data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        daily_aggregation="MINIMUM",
    ),
    "PRECTOTCORR": PowerParameter(
        code="PRECTOTCORR",
        units="mm/day",
        long_name="Precipitation Corrected",
        product="MERRA-2",
        data_category="REANALYSIS_OR_ASSIMILATION_ESTIMATE",
        daily_aggregation="TOTAL",
    ),
    "RH2M": PowerParameter(
        code="RH2M",
        units="%",
        long_name="Relative Humidity at 2 Meters",
        product="MERRA-2",
        data_category="DERIVED",
        daily_aggregation="MEAN",
    ),
    "WS2M": PowerParameter(
        code="WS2M",
        units="m/s",
        long_name="Wind Speed at 2 Meters",
        product="MERRA-2",
        data_category="DERIVED",
        daily_aggregation="MEAN",
    ),
    "ALLSKY_SFC_SW_DWN": PowerParameter(
        code="ALLSKY_SFC_SW_DWN",
        units="MJ/m^2/day",
        long_name="All Sky Surface Shortwave Downward Irradiance",
        product="CERES SYN1deg",
        data_category="SATELLITE_DERIVED_ESTIMATE",
        daily_aggregation="TOTAL",
        first_available_date=date(1984, 1, 1),
    ),
}

#: Minimum useful MVP set agreed in Phase 3A (fits the 20-parameter limit).
RECOMMENDED_PARAMETERS: tuple[str, ...] = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
    "WS2M",
)


# ---------------------------------------------------------------------------
# Request / response value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PowerQuery:
    """A validated-by-caller description of the series we want."""

    latitude: float
    longitude: float
    start: date
    end: date
    parameters: tuple[str, ...] = RECOMMENDED_PARAMETERS
    community: str = COMMUNITY_AGROCLIMATOLOGY
    time_standard: str = TIME_STANDARD_UTC

    @classmethod
    def for_recommended_set(
        cls,
        *,
        latitude: float,
        longitude: float,
        start: date,
        end: date,
    ) -> "PowerQuery":
        return cls(
            latitude=latitude,
            longitude=longitude,
            start=start,
            end=end,
            parameters=RECOMMENDED_PARAMETERS,
        )


@dataclass(frozen=True, slots=True)
class PowerSeries:
    """Daily values for one parameter; ``None`` means POWER reported missing."""

    parameter: PowerParameter
    values: Mapping[date, float | None]

    @property
    def code(self) -> str:
        return self.parameter.code

    @property
    def units(self) -> str:
        return self.parameter.units

    def available_values(self) -> dict[date, float]:
        return {day: value for day, value in self.values.items() if value is not None}


@dataclass(frozen=True, slots=True)
class PowerResponse:
    """Parsed POWER payload with the provenance we must persist."""

    query: PowerQuery
    api_name: str
    api_version: str
    title: str
    sources: tuple[str, ...]
    time_standard: str
    fill_value: float
    requested_latitude: float
    requested_longitude: float
    returned_latitude: float
    returned_longitude: float
    returned_elevation_m: float | None
    series: Mapping[str, PowerSeries]
    messages: tuple[str, ...] = ()

    def parameter(self, code: str) -> PowerSeries:
        try:
            return self.series[code]
        except KeyError as exc:  # pragma: no cover - guarded by parsing
            raise PowerResponseError(f"POWER response has no series for {code!r}.") from exc


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


def build_request_url(query: PowerQuery, *, base_url: str = DAILY_POINT_ENDPOINT) -> str:
    """Build the Daily Point request URL with the mandated fixed arguments."""
    params = {
        "parameters": ",".join(query.parameters),
        "community": query.community,
        "longitude": f"{query.longitude:.6f}".rstrip("0").rstrip("."),
        "latitude": f"{query.latitude:.6f}".rstrip("0").rstrip("."),
        "start": query.start.strftime("%Y%m%d"),
        "end": query.end.strftime("%Y%m%d"),
        "format": RESPONSE_FORMAT_JSON,
        "time-standard": query.time_standard,
    }
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(params)}"


# ---------------------------------------------------------------------------
# Parsing (pure functions, no I/O)
# ---------------------------------------------------------------------------


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PowerResponseError(f"POWER response is missing the {name!r} object.")
    return value


def _optional_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    """Return a float, or ``None`` when the value is not a finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _parse_day(raw_day: str) -> date:
    if not isinstance(raw_day, str) or len(raw_day) != 8 or not raw_day.isdigit():
        raise PowerResponseError(f"POWER returned an unparseable date key: {raw_day!r}.")
    try:
        return date(int(raw_day[0:4]), int(raw_day[4:6]), int(raw_day[6:8]))
    except ValueError as exc:
        raise PowerResponseError(f"POWER returned an invalid date key: {raw_day!r}.") from exc


def parse_daily_response(payload: bytes | str | Mapping[str, Any], query: PowerQuery) -> PowerResponse:
    """Validate a Daily Point JSON payload and normalise it.

    Raises :class:`PowerResponseError` when the payload is malformed, when a
    requested parameter is absent, when units are missing, or when POWER
    silently answers with a different time standard than we asked for.
    """
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PowerResponseError("POWER response is not valid UTF-8.") from exc

    if isinstance(payload, str):
        try:
            data: Any = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise PowerResponseError("POWER response is not valid JSON.") from exc
    else:
        data = payload

    if not isinstance(data, Mapping):
        raise PowerResponseError("POWER response is not a JSON object.")

    header = _require_mapping(data.get("header"), "header")
    metadata = _require_mapping(data.get("parameters"), "parameters")
    properties = _require_mapping(data.get("properties"), "properties")
    values_by_parameter = _require_mapping(properties.get("parameter"), "properties.parameter")

    returned_time_standard = str(header.get("time_standard", "")).upper()
    if returned_time_standard != query.time_standard.upper():
        raise PowerResponseError(
            "POWER answered with time standard "
            f"{returned_time_standard or 'unknown'!r} but {query.time_standard!r} was requested."
        )

    fill_value = _number(header.get("fill_value"))
    if fill_value is None:
        fill_value = DEFAULT_FILL_VALUE

    geometry = _optional_mapping(data.get("geometry"))
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
        raise PowerResponseError("POWER response has no returned coordinates.")
    returned_longitude = _number(coordinates[0])
    returned_latitude = _number(coordinates[1])
    if returned_longitude is None or returned_latitude is None:
        raise PowerResponseError("POWER returned non-numeric coordinates.")
    elevation = _number(coordinates[2]) if len(coordinates) > 2 else None

    api = _optional_mapping(header.get("api"))
    raw_sources = header.get("sources")
    sources = tuple(str(item) for item in raw_sources) if isinstance(raw_sources, list) else ()
    raw_messages = data.get("messages")
    messages = tuple(str(item) for item in raw_messages) if isinstance(raw_messages, list) else ()

    series: dict[str, PowerSeries] = {}
    for code in query.parameters:
        meta = metadata.get(code)
        if not isinstance(meta, Mapping):
            raise PowerResponseError(f"POWER response has no metadata for parameter {code!r}.")
        units = meta.get("units")
        if not isinstance(units, str) or not units.strip():
            raise PowerResponseError(f"POWER response has no units for parameter {code!r}.")

        raw_series = values_by_parameter.get(code)
        if not isinstance(raw_series, Mapping):
            raise PowerResponseError(f"POWER response has no daily values for parameter {code!r}.")

        values: dict[date, float | None] = {}
        for raw_day, raw_value in raw_series.items():
            day = _parse_day(str(raw_day))
            if not (query.start <= day <= query.end):
                continue
            numeric = _number(raw_value)
            values[day] = None if numeric is None or numeric == fill_value else numeric

        parameter = POWER_PARAMETERS[code]
        long_name = meta.get("longname")
        if isinstance(long_name, str) and long_name and long_name != parameter.long_name:
            parameter = PowerParameter(
                code=parameter.code,
                units=units,
                long_name=long_name,
                product=parameter.product,
                data_category=parameter.data_category,
                daily_aggregation=parameter.daily_aggregation,
                first_available_date=parameter.first_available_date,
            )
        elif parameter.units != units:
            # Units are authoritative from POWER, even if they differ from the audit.
            parameter = PowerParameter(
                code=parameter.code,
                units=units,
                long_name=parameter.long_name,
                product=parameter.product,
                data_category=parameter.data_category,
                daily_aggregation=parameter.daily_aggregation,
                first_available_date=parameter.first_available_date,
            )

        series[code] = PowerSeries(parameter=parameter, values=values)

    return PowerResponse(
        query=query,
        api_name=str(api.get("name", "")),
        api_version=str(api.get("version", "")),
        title=str(header.get("title", "")),
        sources=sources,
        time_standard=returned_time_standard,
        fill_value=fill_value,
        requested_latitude=query.latitude,
        requested_longitude=query.longitude,
        returned_latitude=returned_latitude,
        returned_longitude=returned_longitude,
        returned_elevation_m=elevation,
        series=series,
        messages=messages,
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_retry_after(value: str | None) -> float | None:
    """Parse ``Retry-After`` as delta-seconds or an HTTP-date."""
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    return max(0.0, seconds)


def _error_details(body: bytes) -> tuple[str, ...]:
    """Extract POWER's human-readable messages from an error body."""
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        return ()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return (text[:300],)
    if isinstance(data, Mapping):
        messages = data.get("messages")
        if isinstance(messages, list) and messages:
            return tuple(str(item) for item in messages)
        detail = data.get("detail")
        if isinstance(detail, list) and detail:
            return tuple(str(item) for item in detail)
        if isinstance(detail, str):
            return (detail,)
        header = data.get("header")
        if isinstance(header, str):
            return (header,)
    return (text[:300],)


@dataclass(slots=True)
class _CacheEntry:
    expires_at: float
    response: PowerResponse


class PowerClient:
    """Reusable NASA POWER Daily Point client.

    The client is stateless apart from a small, bounded cache of successful
    responses, so one instance can be shared by Celery tasks.

    ``sleep`` and ``monotonic`` are injectable so retry behaviour can be tested
    without real waiting.
    """

    def __init__(
        self,
        *,
        transport: PowerTransport | None = None,
        base_url: str = DAILY_POINT_ENDPOINT,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
        max_retry_after_seconds: float = 30.0,
        cache_ttl_seconds: float = 900.0,
        cache_max_entries: int = 64,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = _utc_today,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if backoff_seconds < 0 or max_retry_after_seconds < 0:
            raise ValueError("Retry delays must be >= 0")
        self._transport = transport or HttpPowerTransport()
        self._base_url = base_url
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._max_retry_after_seconds = max_retry_after_seconds
        self._cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._cache_max_entries = max(1, cache_max_entries)
        self._sleep = sleep
        self._monotonic = monotonic
        self._today = today
        self._cache: dict[tuple[Any, ...], _CacheEntry] = {}

    # -- public API -------------------------------------------------------

    def fetch(self, query: PowerQuery) -> PowerResponse:
        """Fetch and validate one daily series set.

        Raises :class:`PowerConfigurationError` before any network call when the
        query is invalid, :class:`PowerRequestError` for permanent 4xx responses,
        :class:`PowerTransientError` when retries are exhausted, and
        :class:`PowerResponseError` for unusable payloads.
        """
        self.validate_query(query)

        cache_key = self._cache_key(query)
        cached = self._cache.get(cache_key)
        if cached is not None:
            if cached.expires_at > self._monotonic():
                logger.debug("POWER cache hit for %s", cache_key[1:3])
                return cached.response
            self._cache.pop(cache_key, None)

        raw = self._request(query)
        response = parse_daily_response(raw.body, query)
        self._store_in_cache(cache_key, response)
        return response

    def fetch_daily(
        self,
        *,
        latitude: float,
        longitude: float,
        start: date,
        end: date,
        parameters: Sequence[str] = RECOMMENDED_PARAMETERS,
    ) -> PowerResponse:
        """Convenience wrapper around :meth:`fetch`."""
        return self.fetch(
            PowerQuery(
                latitude=latitude,
                longitude=longitude,
                start=start,
                end=end,
                parameters=tuple(parameters),
            )
        )

    def validate_query(self, query: PowerQuery) -> None:
        """Validate coordinates, dates and parameters before contacting POWER."""
        if isinstance(query.latitude, bool) or not isinstance(query.latitude, (int, float)):
            raise PowerConfigurationError("Latitude must be a number.")
        if isinstance(query.longitude, bool) or not isinstance(query.longitude, (int, float)):
            raise PowerConfigurationError("Longitude must be a number.")
        if not -90.0 <= float(query.latitude) <= 90.0:
            raise PowerConfigurationError(
                f"Latitude {query.latitude!r} is outside the valid range [-90, 90]."
            )
        if not -180.0 <= float(query.longitude) <= 180.0:
            raise PowerConfigurationError(
                f"Longitude {query.longitude!r} is outside the valid range [-180, 180]."
            )

        if not isinstance(query.start, date) or not isinstance(query.end, date):
            raise PowerConfigurationError("start and end must be date objects.")
        if query.start > query.end:
            raise PowerConfigurationError(
                f"start ({query.start.isoformat()}) must not be after end ({query.end.isoformat()})."
            )
        if query.start < MINIMUM_SERVICE_DATE:
            raise PowerConfigurationError(
                f"POWER daily data starts on {MINIMUM_SERVICE_DATE.isoformat()}."
            )
        if query.end > self._today():
            raise PowerConfigurationError("end date must not be in the future.")

        parameters = tuple(query.parameters)
        if not parameters:
            raise PowerConfigurationError("At least one POWER parameter is required.")
        if len(parameters) > MAX_PARAMETERS_PER_REQUEST:
            raise PowerConfigurationError(
                f"POWER accepts at most {MAX_PARAMETERS_PER_REQUEST} parameters per request."
            )
        if len(set(parameters)) != len(parameters):
            raise PowerConfigurationError("Duplicate parameters are not allowed.")

        for code in parameters:
            parameter = POWER_PARAMETERS.get(code)
            if parameter is None:
                raise PowerConfigurationError(
                    f"Unknown POWER parameter {code!r}. Verified codes: "
                    f"{', '.join(sorted(POWER_PARAMETERS))}."
                )
            if query.start < parameter.first_available_date:
                raise PowerConfigurationError(
                    f"Parameter {code!r} is only available from "
                    f"{parameter.first_available_date.isoformat()}."
                )

        if query.community != COMMUNITY_AGROCLIMATOLOGY:
            raise PowerConfigurationError(
                f"Only the {COMMUNITY_AGROCLIMATOLOGY!r} community is supported."
            )
        if query.time_standard.upper() != TIME_STANDARD_UTC:
            raise PowerConfigurationError(
                f"Only the {TIME_STANDARD_UTC!r} time standard is supported."
            )

    # -- internals --------------------------------------------------------

    def _request(self, query: PowerQuery) -> RawResponse:
        url = build_request_url(query, base_url=self._base_url)
        attempts_allowed = self._max_retries + 1

        for attempt in range(1, attempts_allowed + 1):
            try:
                raw = self._transport.get(url)
            except (TimeoutError, OSError) as exc:
                self._log_retry(attempt, attempts_allowed, f"transport error: {type(exc).__name__}")
                if attempt == attempts_allowed:
                    raise PowerTransientError(
                        "NASA POWER request failed after "
                        f"{attempts_allowed} attempts ({type(exc).__name__}).",
                        details=(str(exc),),
                    ) from exc
                self._sleep(self._delay_for(attempt, None))
                continue

            if 200 <= raw.status < 300:
                return raw

            retry_after = _parse_retry_after(raw.headers.get("retry-after"))

            if raw.status in RETRYABLE_STATUS_CODES:
                self._log_retry(attempt, attempts_allowed, f"HTTP {raw.status}")
                if attempt == attempts_allowed:
                    raise PowerTransientError(
                        f"NASA POWER kept failing with HTTP {raw.status} after "
                        f"{attempts_allowed} attempts.",
                        details=_error_details(raw.body),
                    )
                self._sleep(self._delay_for(attempt, retry_after))
                continue

            # Permanent client (or unexpected 5xx) failure: do not retry.
            raise PowerRequestError(
                f"NASA POWER rejected the request with HTTP {raw.status}.",
                details=_error_details(raw.body),
            )

        raise PowerTransientError("NASA POWER request failed.")  # pragma: no cover

    def _delay_for(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(retry_after, self._max_retry_after_seconds)
        return min(self._backoff_seconds * (2 ** (attempt - 1)), self._max_retry_after_seconds)

    def _log_retry(self, attempt: int, attempts_allowed: int, reason: str) -> None:
        # Logs never include the query string (coordinates/parameters stay out of logs).
        logger.warning(
            "NASA POWER attempt %d/%d failed (%s); provider=%s",
            attempt,
            attempts_allowed,
            reason,
            "NASA_POWER",
        )

    def _cache_key(self, query: PowerQuery) -> tuple[Any, ...]:
        return (
            round(float(query.latitude), 3),
            round(float(query.longitude), 3),
            query.start.isoformat(),
            query.end.isoformat(),
            tuple(sorted(query.parameters)),
            query.community,
            query.time_standard.upper(),
        )

    def _store_in_cache(self, key: tuple[Any, ...], response: PowerResponse) -> None:
        if self._cache_ttl_seconds <= 0:
            return
        if len(self._cache) >= self._cache_max_entries:
            oldest_key = min(self._cache, key=lambda item: self._cache[item].expires_at)
            self._cache.pop(oldest_key, None)
        self._cache[key] = _CacheEntry(
            expires_at=self._monotonic() + self._cache_ttl_seconds,
            response=response,
        )


__all__ = [
    "COMMUNITY_AGROCLIMATOLOGY",
    "DAILY_POINT_ENDPOINT",
    "DEFAULT_FILL_VALUE",
    "MAX_PARAMETERS_PER_REQUEST",
    "MINIMUM_SERVICE_DATE",
    "POWER_PARAMETERS",
    "RECOMMENDED_PARAMETERS",
    "TIME_STANDARD_UTC",
    "PowerClient",
    "PowerError",
    "PowerParameter",
    "PowerQuery",
    "PowerResponse",
    "PowerSeries",
    "build_request_url",
    "parse_daily_response",
]
