from rest_framework.permissions import BasePermission

from apps.accounts.models import User


STAFF_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.RECEPTIONIST}


class BookingAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in STAFF_ROLES | {User.Role.CUSTOMER}
        )


class BookingWritePermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in STAFF_ROLES
        )


class ReceptionOperationsPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in STAFF_ROLES
        )


class BookingOwnerOrReceptionPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.user.role in STAFF_ROLES or obj.customer_id == request.user.id
