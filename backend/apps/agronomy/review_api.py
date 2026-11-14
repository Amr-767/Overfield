from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsStaffReviewer
from .reviews import review_evidence


class ReviewEvidenceSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=("DATASET", "CALENDAR", "ROTATION_RULE", "CROP_TRAIT"))
    target_id = serializers.IntegerField(min_value=1)
    decision = serializers.ChoiceField(choices=("APPROVED", "REJECTED", "RETURNED"))
    rationale = serializers.CharField(trim_whitespace=True)
    evidence_reference = serializers.CharField(trim_whitespace=True)
    geographic_applicability = serializers.CharField(required=False, allow_blank=True)
    applicability_justification = serializers.CharField(required=False, allow_blank=True)

    def validate_rationale(self, value):
        if not value.strip():
            raise serializers.ValidationError("A review rationale is required.")
        return value

    def validate_evidence_reference(self, value):
        if not value.strip():
            raise serializers.ValidationError("An evidence reference is required.")
        return value


class ReviewEvidenceView(APIView):
    permission_classes = [IsAuthenticated, IsStaffReviewer]

    def post(self, request):
        serializer = ReviewEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = review_evidence(reviewer=request.user, **serializer.validated_data)
        return Response({
            "id": review.pk,
            "target_type": review.target_type,
            "target_id": review.target_id,
            "decision": review.decision,
            "reviewer": review.reviewer_id,
            "rationale": review.rationale,
            "evidence_reference": review.evidence_reference,
            "geographic_applicability": review.geographic_applicability or None,
            "applicability_justification": review.applicability_justification or None,
            "created_at": review.created_at,
        }, status=status.HTTP_201_CREATED)
