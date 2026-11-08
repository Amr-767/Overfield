"""Farm, zone and farmer-context endpoints (Phase 2C/2D).

Every queryset is filtered by ``owner=request.user``, so another farmer's farm
is indistinguishable from a missing farm (HTTP 404) rather than a 403 that would
confirm its existence.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from domain_services.geometry import (
    SRID,
    GeometryValidationError,
    geojson_dict,
    parse_boundary_geojson,
)

from .models import Farm, FarmerContext, FarmZone
from .permissions import IsFarmOwner
from .serializers import (
    BoundaryValidationSerializer,
    FarmerContextSerializer,
    FarmCreateSerializer,
    FarmSerializer,
    FarmUpdateSerializer,
    FarmZoneCreateSerializer,
    FarmZoneSerializer,
)


class FarmViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated farmer's own farms."""

    permission_classes = [IsAuthenticated, IsFarmOwner]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Farm.objects.filter(owner=self.request.user)
            .select_related("context")
            .prefetch_related("zones")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return FarmCreateSerializer
        if self.action in {"update", "partial_update"}:
            return FarmUpdateSerializer
        return FarmSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        return Response(FarmSerializer(farm).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        return Response(FarmSerializer(farm).data)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        farm = self.get_object()
        farm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="validate-boundary")
    def validate_boundary(self, request: Request) -> Response:
        """Validate a candidate boundary without saving it (frontend pre-submit)."""
        payload = BoundaryValidationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            geometry, area = parse_boundary_geojson(payload.validated_data["boundary"])
        except GeometryValidationError as exc:
            return Response({exc.field: [exc.message]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "valid": True,
                "srid": SRID,
                "area_hectares": str(area),
                "area_method": "postgis_geography",
                "geometry": geojson_dict(geometry),
            }
        )

    @action(detail=True, methods=["get", "post"], url_path="zones")
    def zones(self, request: Request, pk: str | None = None) -> Response:
        farm = self.get_object()

        if request.method == "GET":
            queryset = farm.zones.all()
            page = self.paginate_queryset(queryset)
            if page is not None:
                return self.get_paginated_response(FarmZoneSerializer(page, many=True).data)
            return Response(FarmZoneSerializer(queryset, many=True).data)

        serializer = FarmZoneCreateSerializer(data=request.data, context={"farm": farm})
        serializer.is_valid(raise_exception=True)
        zone: FarmZone = serializer.save()
        return Response(FarmZoneSerializer(zone).data, status=status.HTTP_201_CREATED)


class FarmContextView(APIView):
    """GET/PUT/PATCH ``/api/v1/farms/{id}/context/`` — farmer inputs for one farm."""

    permission_classes = [IsAuthenticated, IsFarmOwner]

    def _farm(self, request: Request, farm_id: int) -> Farm:
        farm = get_object_or_404(Farm, pk=farm_id, owner=request.user)
        self.check_object_permissions(request, farm)
        return farm

    def get(self, request: Request, farm_id: int) -> Response:
        farm = self._farm(request, farm_id)
        context, _ = FarmerContext.objects.get_or_create(farm=farm)
        return Response(FarmerContextSerializer(context).data)

    def put(self, request: Request, farm_id: int) -> Response:
        return self._save(request, farm_id, partial=False)

    def patch(self, request: Request, farm_id: int) -> Response:
        return self._save(request, farm_id, partial=True)

    def _save(self, request: Request, farm_id: int, partial: bool) -> Response:
        farm = self._farm(request, farm_id)
        context, _ = FarmerContext.objects.get_or_create(farm=farm)
        serializer = FarmerContextSerializer(context, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        context.refresh_from_db()
        return Response(FarmerContextSerializer(context).data)
