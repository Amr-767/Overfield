"""Foundation API views (Phase 1B)."""

from __future__ import annotations

from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Public health check for local development and frontend connectivity.

    Contract: GET /api/v1/health/
    """

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request: Request) -> Response:
        database_status = "connected"
        overall = "healthy"
        http_status = status.HTTP_200_OK

        try:
            connection.ensure_connection()
        except Exception:
            database_status = "unavailable"
            overall = "unhealthy"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": overall,
                "database": database_status,
                "timestamp": timezone.now().isoformat().replace("+00:00", "Z"),
            },
            status=http_status,
        )
