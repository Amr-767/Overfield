"""Serializers for registration and the farmer profile."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import FarmerProfile

User = get_user_model()


class FarmerProfileSerializer(serializers.ModelSerializer):
    """Profile fields that are safe for the owner to read and update."""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)

    class Meta:
        model = FarmerProfile
        fields = ["username", "display_name", "email", "preferred_language", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def update(self, instance: FarmerProfile, validated_data: dict) -> FarmerProfile:
        user_data = validated_data.pop("user", {})
        instance = super().update(instance, validated_data)
        if user_data:
            user = instance.user
            for field, value in user_data.items():
                setattr(user, field, value)
            user.save(update_fields=list(user_data))
        return instance


class RegisterSerializer(serializers.Serializer):
    """Create a farmer account. ``username`` is the login identifier (Phase 0 contract)."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    preferred_language = serializers.CharField(max_length=8, required=False, default="en")

    def validate_username(self, value: str) -> str:
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value: str) -> str:
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data: dict) -> FarmerProfile:
        profile_data = {
            "display_name": validated_data.pop("display_name", ""),
            "preferred_language": validated_data.pop("preferred_language", "en"),
        }
        password = validated_data.pop("password")
        user = User(username=validated_data["username"], email=validated_data.get("email", ""))
        user.set_password(password)
        user.save()
        return FarmerProfile.objects.create(user=user, **profile_data)

    def to_representation(self, instance: FarmerProfile) -> dict:
        return {
            "id": instance.user_id,
            "username": instance.user.get_username(),
            "email": instance.user.email,
            "display_name": instance.display_name,
            "preferred_language": instance.preferred_language,
        }


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """PATCH ``/me/`` payload: profile fields plus a mutable email address."""

    email = serializers.EmailField(source="user.email", required=False, allow_blank=True)

    class Meta:
        model = FarmerProfile
        fields = ["display_name", "preferred_language", "email"]

    def update(self, instance: FarmerProfile, validated_data: dict) -> FarmerProfile:
        user_data = validated_data.pop("user", {})
        instance = super().update(instance, validated_data)
        if "email" in user_data:
            email = user_data["email"]
            if email and User.objects.filter(email__iexact=email).exclude(pk=instance.user_id).exists():
                raise serializers.ValidationError({"email": ["A user with that email already exists."]})
            instance.user.email = email
            instance.user.save(update_fields=["email"])
        return instance
