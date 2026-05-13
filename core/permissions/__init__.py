"""
Reusable DRF permission classes shared across API views.

Place: core/permissions/__init__.py
"""

from rest_framework.permissions import BasePermission


class IsVerifiedUser(BasePermission):
    """
    Allow access only to users whose email has been confirmed.
    Use on endpoints that require full account activation
    (e.g. sending emails, adding domains).
    """
    message = "Email address must be verified before accessing this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_verified
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission: allow access only if the requesting user
    owns the object (obj.user == request.user) or is staff.
    The view must call self.check_object_permissions(request, obj).
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        owner = getattr(obj, "user", None)
        return owner == request.user


class HasAPIKey(BasePermission):
    """
    Allow access only when the request was authenticated via an APIKey
    (as opposed to session auth).  Useful for endpoints that should only
    be accessible programmatically.
    """
    message = "This endpoint requires API key authentication."

    def has_permission(self, request, view):
        from apps.authentication.models import APIKey
        return isinstance(request.auth, APIKey)


class QuotaNotExceeded(BasePermission):
    """
    Block sending endpoints when the user has exceeded their monthly quota.
    Attach to POST /v1/send and POST /v1/send/bulk.
    """
    message = "Monthly sending quota exceeded. Upgrade your plan or wait for quota reset."

    def has_permission(self, request, view):
        return not request.user.quota_exceeded