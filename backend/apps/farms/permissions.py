"""Object-level permissions for farm data."""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from .models import Farm


class IsFarmOwner(BasePermission):
    """Defence in depth: views already filter querysets by owner.

    Keeping this check as well means an accidentally unscoped queryset still
    cannot expose another farmer's data.
    """

    message = "You do not have access to this farm."

    def has_object_permission(self, request, view, obj) -> bool:
        owner = getattr(obj, "owner", None) or getattr(getattr(obj, "farm", None), "owner", None)
        if owner is None:
            return False
        return owner == request.user

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)


__all__ = ["IsFarmOwner", "Farm"]
