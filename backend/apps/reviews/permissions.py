from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.CUSTOMER)


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {User.Role.MANAGER, User.Role.ADMIN}
        )


class IsPendingReviewOwner(IsCustomer):
    def has_object_permission(self, request, view, obj):
        return obj.customer_id == request.user.id and obj.status == obj.Status.PENDING
