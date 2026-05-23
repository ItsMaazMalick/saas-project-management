from rest_framework.permissions import BasePermission
from .models import UserRole


class IsCompanyAdmin(BasePermission):
    """Only company admins can access."""
    message = "You must be a company admin to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )


class IsManagerOrAdmin(BasePermission):
    """Managers and admins can access."""
    message = "You must be a manager or admin to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.ADMIN, UserRole.MANAGER)
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level: allow if user owns the object or is admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return True
        user_field = getattr(obj, "user", None) or getattr(obj, "assigned_to", None)
        return user_field == request.user


class IsSameTenant(BasePermission):
    """Ensures the object belongs to the same company as the requesting user."""
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        obj_company = getattr(obj, "company", None)
        return obj_company == request.user.company
