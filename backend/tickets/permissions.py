from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Only admin users can access.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role == 'admin'
        )


class IsAgent(permissions.BasePermission):
    """
    Only staff users (or admin) can access.
    """

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            hasattr(request.user, 'profile') and
            request.user.profile.role in ['staff', 'admin']
        )
