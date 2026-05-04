from rest_framework.permissions import BasePermission

from apps.accounts.models import UserRole


def is_admin_user(user) -> bool:
    return bool(user and user.is_authenticated and user.is_platform_admin)


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsSellerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.can_sell)


class IsBidderSellerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in {UserRole.BIDDER, UserRole.SELLER, UserRole.ADMIN}
        )
