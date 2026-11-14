from rest_framework.permissions import BasePermission


class IsStaffReviewer(BasePermission):
    """Only authenticated staff may moderate agricultural evidence."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
