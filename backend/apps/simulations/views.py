"""Owner-scoped scenario simulation API (Phase 6.3).

Routes
------
``POST /api/v1/farms/{farm_id}/simulations/``  create a stored run
``GET  /api/v1/farms/{farm_id}/simulations/``  recent runs for the farm
``GET  /api/v1/simulations/{simulation_id}/``  stored run
``GET  /api/v1/simulations/{simulation_id}/steps/`` stored checkpoints

Anonymous requests are ``401``; another farmer's farm or run is ``404`` (no
existence leak).
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.farms.models import Farm

from .models import SimulationRun
from .serializers import CreateSimulationSerializer, SimulationQuerySerializer
from .service import (
    ScenarioValidationError,
    create_simulation,
    simulation_payload,
    steps_payload,
)


class FarmSimulationView(APIView):
    """Create or list simulation runs for one owned farm."""

    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id: int) -> Response:
        farm = get_object_or_404(Farm, pk=farm_id, owner=request.user)
        query = SimulationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        runs = (
            SimulationRun.objects.filter(farm=farm)
            .prefetch_related("steps")
            .order_by("-created_at", "-id")[: query.validated_data["limit"]]
        )
        payload = [simulation_payload(run) for run in runs]
        return Response({"count": len(payload), "results": payload}, status=status.HTTP_200_OK)

    def post(self, request, farm_id: int) -> Response:
        farm = get_object_or_404(Farm, pk=farm_id, owner=request.user)
        serializer = CreateSimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            run = create_simulation(
                farm,
                requested_by=request.user,
                scenario_mode=data["scenario_mode"],
                temperature_delta_c=data.get("temperature_delta_c"),
                rainfall_multiplier=data.get("rainfall_multiplier"),
                window_days=data.get("window_days"),
            )
        except ScenarioValidationError as exc:
            return Response(
                {"scenario_mode": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST
            )
        run = SimulationRun.objects.prefetch_related("steps").get(pk=run.pk)
        return Response(simulation_payload(run), status=status.HTTP_201_CREATED)


class SimulationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, simulation_id) -> Response:
        run = get_object_or_404(
            SimulationRun.objects.select_related("farm").prefetch_related("steps"),
            pk=simulation_id,
            farm__owner=request.user,
        )
        return Response(simulation_payload(run), status=status.HTTP_200_OK)


class SimulationStepsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, simulation_id) -> Response:
        run = get_object_or_404(
            SimulationRun.objects.prefetch_related("steps"),
            pk=simulation_id,
            farm__owner=request.user,
        )
        return Response(steps_payload(run), status=status.HTTP_200_OK)


__all__ = ["FarmSimulationView", "SimulationDetailView", "SimulationStepsView"]
