"""Account profile extension for the built-in Django user.

The project uses ``django.contrib.auth.User`` as the single identity model
(ADR-019) and adds a one-to-one farmer profile for fields the platform needs
but Django's user does not carry.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class FarmerProfile(models.Model):
    """Additional farmer-facing profile data for an authenticated user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farmer_profile",
    )
    display_name = models.CharField(max_length=120, blank=True)
    preferred_language = models.CharField(
        max_length=8,
        default="en",
        help_text="Short language code used for farmer-facing text.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "farmer profile"
        verbose_name_plural = "farmer profiles"

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()
