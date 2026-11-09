"""HTTP transport for the NASA POWER provider (Phase 3B).

Deliberately separate from parsing: this module knows only how to perform a
GET and return status, headers and body. It uses ``http.client`` from the
standard library so we can apply **separate connect and read timeouts** without
adding a third-party dependency.
"""

from __future__ import annotations

import http.client
from dataclasses import dataclass, field
from typing import Mapping, Protocol
from urllib.parse import urlsplit, urlunsplit

DEFAULT_USER_AGENT = "AgroSpaceQuest/0.1 (NASA Space Apps 2026; POWER client)"


@dataclass(frozen=True, slots=True)
class RawResponse:
    """Minimal, transport-agnostic HTTP response."""

    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


class PowerTransport(Protocol):
    """Anything able to perform a GET and return a :class:`RawResponse`."""

    def get(self, url: str) -> RawResponse:  # pragma: no cover - protocol
        ...


class HttpPowerTransport:
    """Standard-library HTTP transport with separate connect/read timeouts.

    ``http.client`` is used directly instead of ``urllib.request`` because the
    latter exposes a single socket timeout and raises on 4xx/5xx, which would
    hide ``Retry-After`` handling from the client.
    """

    def __init__(
        self,
        *,
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if connect_timeout <= 0 or read_timeout <= 0:
            raise ValueError("Power timeouts must be positive.")
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._user_agent = user_agent

    def get(self, url: str) -> RawResponse:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError(f"Unsupported POWER URL: {parts.scheme or 'no scheme'}")

        connection_class = (
            http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        )
        connection = connection_class(parts.hostname, parts.port, timeout=self._connect_timeout)
        try:
            connection.connect()
            if connection.sock is not None:
                # Apply the (usually longer) read timeout once connected.
                connection.sock.settimeout(self._read_timeout)
            path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
            connection.request(
                "GET",
                path,
                headers={"Accept": "application/json", "User-Agent": self._user_agent},
            )
            response = connection.getresponse()
            body = response.read()
            headers = {key.lower(): value for key, value in response.getheaders()}
            return RawResponse(status=response.status, headers=headers, body=body)
        finally:
            connection.close()


__all__ = [
    "DEFAULT_USER_AGENT",
    "HttpPowerTransport",
    "PowerTransport",
    "RawResponse",
]
