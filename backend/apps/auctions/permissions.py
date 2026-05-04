from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuctionOwnerOrAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(user and user.is_authenticated and user.can_sell)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_platform_admin or obj.created_by_id == user.id)
        )


class IsLotOwnerOrAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(user and user.is_authenticated and user.can_sell)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_platform_admin or obj.auction.created_by_id == user.id)
        )

