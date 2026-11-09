"""NASA POWER client tests (Phase 3B) — fully mocked, no network access."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Iterable

from django.test import SimpleTestCase

from apps.earth_data.exceptions import (
    PowerConfigurationError,
    PowerRequestError,
    PowerResponseError,
    PowerTransientError,
)
from apps.earth_data.providers.power import (
    COMMUNITY_AGROCLIMATOLOGY,
    MAX_PARAMETERS_PER_REQUEST,
    POWER_PARAMETERS,
    RECOMMENDED_PARAMETERS,
    TIME_STANDARD_UTC,
    PowerClient,
    PowerQuery,
    build_request_url,
    parse_daily_response,
)
from apps.earth_data.providers.power_transport import RawResponse

DATES = [date(2024, 1, day) for day in range(1, 8)]
VALUES: dict[str, list[float]] = {
    "T2M": [16.15, 16.43, 15.90, 15.12, 15.60, 16.68, 15.42],
    "T2M_MAX": [22.23, 22.68, 21.82, 22.11, 22.84, 23.60, 24.58],
    "T2M_MIN": [11.05, 11.20, 10.80, 9.90, 10.20, 11.40, 10.10],
    "PRECTOTCORR": [0.0, 0.0, 0.0, 0.0, 0.08, 0.01, 0.42],
    "RH2M": [62.0, 60.5, 58.0, 55.2, 61.4, 63.0, 59.9],
    "WS2M": [2.1, 2.4, 1.9, 2.6, 3.1, 2.2, 1.8],
    "ALLSKY_SFC_SW_DWN": [12.24, 12.60, 11.90, 12.05, 12.80, 13.10, 12.45],
}


def payload(
    parameters: Iterable[str] = RECOMMENDED_PARAMETERS,
    *,
    dates: list[date] = DATES,
    time_standard: str = "UTC",
    fill_value: float = -999.0,
    coordinates: list[float] | None = None,
    units: dict[str, str] | None = None,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a payload shaped exactly like the verified POWER response."""
    codes = list(parameters)
    meta: dict[str, Any] = {}
    series: dict[str, Any] = {}
    for code in codes:
        unit = (units or {}).get(code, POWER_PARAMETERS[code].units)
        meta[code] = {"units": unit, "longname": POWER_PARAMETERS[code].long_name}
        day_values = {
            day.strftime("%Y%m%d"): value for day, value in zip(dates, VALUES[code], strict=False)
        }
        day_values.update((overrides or {}).get(code, {}))
        series[code] = day_values

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": coordinates or [30.95, 30.79, 4.96]},
        "header": {
            "title": "NASA/POWER Source Native Resolution Daily Data",
            "api": {"version": "v2.10.3", "name": "POWER Daily API"},
            "sources": ["MERRA2", "SYN1DEG", "POWER"],
            "fill_value": fill_value,
            "time_standard": time_standard,
            "start": dates[0].strftime("%Y%m%d"),
            "end": dates[-1].strftime("%Y%m%d"),
        },
        "messages": [],
        "parameters": meta,
        "properties": {"parameter": series},
        "times": {"data": 0.845, "process": 0.01},
    }


def body(data: Any) -> RawResponse:
    return RawResponse(status=200, headers={"content-type": "application/json"}, body=json.dumps(data).encode())


class FakeTransport:
    """Returns queued responses (or raises queued exceptions) and records URLs."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def get(self, url: str) -> RawResponse:
        self.calls.append(url)
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def make_query(**overrides: Any) -> PowerQuery:
    defaults: dict[str, Any] = {
        "latitude": 30.79,
        "longitude": 30.95,
        "start": DATES[0],
        "end": DATES[-1],
        "parameters": RECOMMENDED_PARAMETERS,
    }
    defaults.update(overrides)
    return PowerQuery(**defaults)


def make_client(transport: FakeTransport, **overrides: Any) -> PowerClient:
    options: dict[str, Any] = {
        "transport": transport,
        "max_retries": 2,
        "backoff_seconds": 0.5,
        "cache_ttl_seconds": 0.0,  # cache tested separately
        "sleep": lambda _seconds: None,
        "today": lambda: date(2024, 1, 10),
    }
    options.update(overrides)
    return PowerClient(**options)


class ParseResponseTests(SimpleTestCase):
    def test_successful_response_preserves_values_units_and_provenance(self) -> None:
        response = parse_daily_response(json.dumps(payload()), make_query())

        self.assertEqual(response.api_version, "v2.10.3")
        self.assertEqual(response.api_name, "POWER Daily API")
        self.assertEqual(response.time_standard, "UTC")
        self.assertEqual(response.sources, ("MERRA2", "SYN1DEG", "POWER"))
        self.assertEqual(response.fill_value, -999.0)
        self.assertEqual(response.returned_longitude, 30.95)
        self.assertEqual(response.returned_latitude, 30.79)
        self.assertEqual(response.returned_elevation_m, 4.96)

        t2m = response.parameter("T2M")
        self.assertEqual(t2m.units, "C")
        self.assertEqual(t2m.values[date(2024, 1, 1)], 16.15)
        self.assertEqual(t2m.values[date(2024, 1, 7)], 15.42)
        self.assertEqual(len(t2m.values), 7)

    def test_multiple_parameters_are_all_normalised(self) -> None:
        response = parse_daily_response(json.dumps(payload()), make_query())
        self.assertEqual(set(response.series), set(RECOMMENDED_PARAMETERS))
        self.assertEqual(response.parameter("PRECTOTCORR").units, "mm/day")
        self.assertEqual(response.parameter("ALLSKY_SFC_SW_DWN").units, "MJ/m^2/day")
        self.assertEqual(response.parameter("WS2M").units, "m/s")

    def test_missing_values_become_none_not_sentinel(self) -> None:
        data = payload(overrides={"T2M": {"20240103": -999.0}, "PRECTOTCORR": {"20240105": -999.0}})
        response = parse_daily_response(data, make_query())

        self.assertIsNone(response.parameter("T2M").values[date(2024, 1, 3)])
        self.assertIsNone(response.parameter("PRECTOTCORR").values[date(2024, 1, 5)])
        self.assertEqual(response.parameter("T2M").values[date(2024, 1, 2)], 16.43)
        # Null is also treated as missing, not zero.
        self.assertIsNone(
            parse_daily_response(
                payload(overrides={"T2M": {"20240104": None}}), make_query()
            ).parameter("T2M").values[date(2024, 1, 4)]
        )

    def test_units_from_power_are_authoritative(self) -> None:
        data = payload(units={"T2M": "K"})
        response = parse_daily_response(data, make_query())
        self.assertEqual(response.parameter("T2M").units, "K")

    def test_dates_outside_the_requested_range_are_dropped(self) -> None:
        data = payload(overrides={"T2M": {"20240109": 99.0}})
        response = parse_daily_response(data, make_query())
        self.assertNotIn(date(2024, 1, 9), response.parameter("T2M").values)

    def test_malformed_json_is_a_response_error(self) -> None:
        with self.assertRaises(PowerResponseError):
            parse_daily_response(b"<html>gateway</html>", make_query())

    def test_missing_header_is_a_response_error(self) -> None:
        data = payload()
        data.pop("header")
        with self.assertRaises(PowerResponseError):
            parse_daily_response(data, make_query())

    def test_missing_parameter_values_is_a_response_error(self) -> None:
        # The payload only carries T2M; the next requested code is reported.
        data = payload(parameters=["T2M"])
        with self.assertRaises(PowerResponseError) as ctx:
            parse_daily_response(data, make_query())
        self.assertIn("T2M_MAX", str(ctx.exception))

    def test_missing_units_is_a_response_error(self) -> None:
        data = payload(units={"T2M": ""})
        with self.assertRaises(PowerResponseError) as ctx:
            parse_daily_response(data, make_query())
        self.assertIn("units", str(ctx.exception))

    def test_time_standard_mismatch_is_a_response_error(self) -> None:
        data = payload(time_standard="LST")
        with self.assertRaises(PowerResponseError) as ctx:
            parse_daily_response(data, make_query())
        self.assertIn("LST", str(ctx.exception))


class RequestValidationTests(SimpleTestCase):
    def test_invalid_dates_are_rejected_before_any_request(self) -> None:
        transport = FakeTransport([])
        client = make_client(transport)

        with self.assertRaises(PowerConfigurationError):
            client.fetch(make_query(start=date(2024, 1, 7), end=date(2024, 1, 1)))
        with self.assertRaises(PowerConfigurationError):
            client.fetch(make_query(start=date(1980, 12, 31), end=date(1981, 1, 2)))
        with self.assertRaises(PowerConfigurationError):
            client.fetch(make_query(end=date(2024, 2, 1)))  # after injected "today"

        self.assertEqual(transport.calls, [])

    def test_invalid_coordinates_are_rejected_before_any_request(self) -> None:
        transport = FakeTransport([])
        client = make_client(transport)

        for query in (
            make_query(latitude=95.0),
            make_query(latitude=-90.5),
            make_query(longitude=181.0),
            make_query(longitude=-200.0),
            make_query(latitude="30.79"),  # type: ignore[arg-type]
        ):
            with self.assertRaises(PowerConfigurationError):
                client.fetch(query)

        self.assertEqual(transport.calls, [])

    def test_unknown_parameter_is_rejected(self) -> None:
        transport = FakeTransport([])
        with self.assertRaises(PowerConfigurationError) as ctx:
            make_client(transport).fetch(make_query(parameters=("T2M", "BOGUSPARAM")))
        self.assertIn("BOGUSPARAM", str(ctx.exception))
        self.assertEqual(transport.calls, [])

    def test_parameter_limit_and_duplicates_are_enforced(self) -> None:
        transport = FakeTransport([])
        client = make_client(transport)
        too_many = tuple(list(POWER_PARAMETERS) * 3)[: MAX_PARAMETERS_PER_REQUEST + 1]
        with self.assertRaises(PowerConfigurationError):
            client.fetch(make_query(parameters=too_many))
        with self.assertRaises(PowerConfigurationError):
            client.fetch(make_query(parameters=("T2M", "T2M")))
        self.assertEqual(transport.calls, [])

    def test_solar_parameter_rejects_pre_1984_start(self) -> None:
        transport = FakeTransport([])
        with self.assertRaises(PowerConfigurationError) as ctx:
            make_client(transport).fetch(
                make_query(
                    start=date(1981, 1, 1),
                    end=date(1981, 1, 5),
                    parameters=("ALLSKY_SFC_SW_DWN",),
                )
            )
        self.assertIn("1984-01-01", str(ctx.exception))
        self.assertEqual(transport.calls, [])


class RequestUrlTests(SimpleTestCase):
    def test_url_requests_json_agroclimatology_and_utc(self) -> None:
        url = build_request_url(make_query())

        self.assertIn("format=JSON", url)
        self.assertIn(f"community={COMMUNITY_AGROCLIMATOLOGY}", url)
        self.assertIn(f"time-standard={TIME_STANDARD_UTC}", url)
        self.assertIn("start=20240101", url)
        self.assertIn("end=20240107", url)
        self.assertIn("parameters=T2M%2CT2M_MAX", url)
        self.assertIn("latitude=30.79", url)
        self.assertIn("longitude=30.95", url)

    def test_client_sends_the_built_url(self) -> None:
        transport = FakeTransport([body(payload())])
        make_client(transport).fetch(make_query())
        self.assertEqual(len(transport.calls), 1)
        self.assertIn("community=AG", transport.calls[0])
        self.assertIn("time-standard=UTC", transport.calls[0])


class RetryTests(SimpleTestCase):
    def test_timeout_is_retried_then_succeeds(self) -> None:
        transport = FakeTransport([TimeoutError("connect timed out"), body(payload())])
        sleeps: list[float] = []
        client = make_client(transport, sleep=sleeps.append)

        response = client.fetch(make_query())

        self.assertEqual(response.parameter("T2M").values[date(2024, 1, 1)], 16.15)
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(sleeps, [0.5])

    def test_timeout_exhausts_bounded_retries(self) -> None:
        transport = FakeTransport([TimeoutError("t1"), OSError("t2"), TimeoutError("t3")])
        sleeps: list[float] = []
        client = make_client(transport, sleep=sleeps.append)

        with self.assertRaises(PowerTransientError) as ctx:
            client.fetch(make_query())

        self.assertEqual(len(transport.calls), 3)  # 1 attempt + 2 retries
        self.assertEqual(sleeps, [0.5, 1.0])  # exponential backoff
        self.assertIn("3 attempts", str(ctx.exception))

    def test_429_respects_retry_after(self) -> None:
        transport = FakeTransport(
            [
                RawResponse(status=429, headers={"retry-after": "7"}, body=b'{"messages":["slow down"]}'),
                body(payload()),
            ]
        )
        sleeps: list[float] = []
        client = make_client(transport, sleep=sleeps.append)

        response = client.fetch(make_query())

        self.assertEqual(response.time_standard, "UTC")
        self.assertEqual(sleeps, [7.0])

    def test_retry_after_http_date_is_parsed(self) -> None:
        from email.utils import format_datetime
        from datetime import datetime, timedelta, timezone

        soon = datetime.now(timezone.utc) + timedelta(seconds=6)
        transport = FakeTransport(
            [
                RawResponse(status=429, headers={"retry-after": format_datetime(soon, usegmt=True)}, body=b""),
                body(payload()),
            ]
        )
        sleeps: list[float] = []
        make_client(transport, sleep=sleeps.append).fetch(make_query())
        self.assertEqual(len(sleeps), 1)
        self.assertTrue(4.0 <= sleeps[0] <= 7.0, sleeps)

    def test_retry_after_is_capped(self) -> None:
        transport = FakeTransport(
            [
                RawResponse(status=503, headers={"retry-after": "9999"}, body=b""),
                body(payload()),
            ]
        )
        sleeps: list[float] = []
        make_client(transport, sleep=sleeps.append, max_retry_after_seconds=30.0).fetch(make_query())
        self.assertEqual(sleeps, [30.0])

    def test_503_is_retried_then_succeeds(self) -> None:
        transport = FakeTransport(
            [RawResponse(status=503, body=b""), RawResponse(status=502, body=b""), body(payload())]
        )
        client = make_client(transport)

        response = client.fetch(make_query())
        self.assertIn("T2M", response.series)
        self.assertEqual(len(transport.calls), 3)

    def test_repeated_5xx_ends_in_transient_error(self) -> None:
        transport = FakeTransport([RawResponse(status=500, body=b"") for _ in range(3)])
        client = make_client(transport)

        with self.assertRaises(PowerTransientError) as ctx:
            client.fetch(make_query())
        self.assertEqual(len(transport.calls), 3)
        self.assertIn("500", str(ctx.exception))

    def test_422_is_permanent_and_not_retried(self) -> None:
        power_error = {
            "header": "The POWER Daily API failed to complete your request",
            "messages": ["One of your parameters is incorrect: BOGUSPARAM."],
        }
        transport = FakeTransport(
            [RawResponse(status=422, headers={}, body=json.dumps(power_error).encode())]
        )
        client = make_client(transport)

        with self.assertRaises(PowerRequestError) as ctx:
            client.fetch(make_query())
        self.assertEqual(len(transport.calls), 1)
        self.assertIn("BOGUSPARAM", str(ctx.exception.details))
        self.assertIn("422", str(ctx.exception))

    def test_400_is_not_retried(self) -> None:
        transport = FakeTransport([RawResponse(status=400, body=b'{"detail":[{"msg":"bad"}]}')])
        with self.assertRaises(PowerRequestError):
            make_client(transport).fetch(make_query())
        self.assertEqual(len(transport.calls), 1)


class CacheTests(SimpleTestCase):
    def test_identical_queries_are_not_requested_twice(self) -> None:
        transport = FakeTransport([body(payload())])
        client = make_client(transport, cache_ttl_seconds=900.0)

        first = client.fetch(make_query())
        second = client.fetch(make_query())

        self.assertEqual(len(transport.calls), 1)
        self.assertIs(first, second)

    def test_cache_can_be_disabled(self) -> None:
        transport = FakeTransport([body(payload()), body(payload())])
        client = make_client(transport, cache_ttl_seconds=0.0)

        client.fetch(make_query())
        client.fetch(make_query())

        self.assertEqual(len(transport.calls), 2)

    def test_cache_key_separates_different_parameter_sets(self) -> None:
        transport = FakeTransport([body(payload(parameters=["T2M"])), body(payload())])
        client = make_client(transport, cache_ttl_seconds=900.0)

        client.fetch(make_query(parameters=("T2M",)))
        client.fetch(make_query())

        self.assertEqual(len(transport.calls), 2)

    def test_expired_cache_entry_is_refetched(self) -> None:
        transport = FakeTransport([body(payload()), body(payload())])
        clock = [100.0]
        client = make_client(transport, cache_ttl_seconds=10.0, monotonic=lambda: clock[0])

        client.fetch(make_query())
        clock[0] += 11.0
        client.fetch(make_query())

        self.assertEqual(len(transport.calls), 2)
