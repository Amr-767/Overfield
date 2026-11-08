"""Authentication and profile endpoints (Phase 2A)."""

from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FarmerProfile
from .serializers import FarmerProfileSerializer, ProfileUpdateSerializer, RegisterSerializer


class RegisterView(APIView):
    """POST /api/v1/auth/register/ — public farmer registration."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(serializer.to_representation(profile), status=status.HTTP_201_CREATED)


class MeView(APIView):
    """GET/PATCH /api/v1/me/ — the authenticated farmer's own profile."""

    permission_classes = [IsAuthenticated]

    def _profile(self, request: Request) -> FarmerProfile:
        profile, _ = FarmerProfile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request: Request) -> Response:
        return Response(FarmerProfileSerializer(self._profile(request)).data)

    def patch(self, request: Request) -> Response:
        profile = self._profile(request)
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(FarmerProfileSerializer(profile).data)

    def put(self, request: Request) -> Response:
        return self.patch(request)
