"""Owner-scoped rotation assessment API."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.farms.models import Farm

from .models import RotationRecommendation
from .recommendations import generate_recommendation, recommendation_payload


class GenerateRotationSerializer(serializers.Serializer):
    region_code = serializers.CharField(required=False, allow_blank=False, max_length=80)
    planning_seasons = serializers.IntegerField(min_value=1, max_value=12, default=4)
    planning_start_date = serializers.DateField(required=False)
    priority_weights = serializers.DictField(child=serializers.FloatField(min_value=0), required=False)

    def validate_priority_weights(self, value):
        allowed = {"water_conservation", "soil_regeneration", "market_income", "forage_value"}
        if set(value) - allowed:
            raise serializers.ValidationError(f"Allowed priority keys: {sorted(allowed)}.")
        if not value or abs(sum(value.values()) - 1.0) > 0.01:
            raise serializers.ValidationError("Named priority weights must sum to 1 (±0.01).")
        return value


class FarmRecommendationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, farm_id: int):
        farm = get_object_or_404(Farm, pk=farm_id, owner=request.user)
        serializer = GenerateRotationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = generate_recommendation(
            farm=farm,
            requested_by=request.user,
            region_code=serializer.validated_data.get("region_code"),
            planning_seasons=serializer.validated_data["planning_seasons"],
            priorities=serializer.validated_data.get("priority_weights"),
            planning_start_date=serializer.validated_data.get("planning_start_date"),
        )
        return Response(recommendation_payload(result), status=status.HTTP_201_CREATED)


class RecommendationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, recommendation_id):
        result = get_object_or_404(
            RotationRecommendation.objects.select_related("farm"),
            pk=recommendation_id,
            farm__owner=request.user,
        )
        return Response(recommendation_payload(result))


class RecommendationCompareView(APIView):
    """Compare two reproducible snapshots without manufacturing preference scores."""
    permission_classes = [IsAuthenticated]

    def get(self, request, recommendation_id):
        other_id = request.query_params.get("with")
        if not other_id:
            raise serializers.ValidationError({"with": ["A second recommendation_id is required."]})
        ids = [recommendation_id, other_id]
        results = list(RotationRecommendation.objects.filter(pk__in=ids, farm__owner=request.user))
        if len(results) != 2:
            from django.http import Http404
            raise Http404
        first, second = sorted(results, key=lambda item: str(item.pk))
        if str(first.pk) != str(recommendation_id):
            first, second = second, first
        return Response({
            "recommendation_ids": [str(first.pk), str(second.pk)],
            "same_input": first.input_sha256 == second.input_sha256,
            "assessments": [recommendation_payload(first), recommendation_payload(second)],
            "comparison_method": "Evidence and constraints are compared as recorded; no objective ranking or numeric score is produced.",
        })


class RecommendationExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, recommendation_id):
        result = get_object_or_404(
            RotationRecommendation.objects.select_related("farm"),
            pk=recommendation_id,
            farm__owner=request.user,
        )
        payload = recommendation_payload(result)
        return Response({
            "recommendation_id": payload["recommendation_id"],
            "explanation": payload["explanation"],
            "missing": payload["missing"],
            "constraints": payload["constraints"],
            "rejected_alternatives": payload["rejected_alternatives"],
            "environmental_inputs": payload["environmental_digest"],
            "crop_profiles": payload["crop_profiles"],
            "data_limitations": payload["data_limitations"],
            "input_sha256": payload["input_sha256"],
        })
