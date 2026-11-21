from rest_framework.permissions import BasePermission

from .models import User


class HasRole(BasePermission):
    allowed_roles = frozenset()

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.allowed_roles
        )


class IsAdmin(HasRole):
    allowed_roles = frozenset({User.Role.ADMIN})


class IsManager(HasRole):
    allowed_roles = frozenset({User.Role.MANAGER})


class IsReceptionist(HasRole):
    allowed_roles = frozenset({User.Role.RECEPTIONIST})


class IsHousekeeping(HasRole):
    allowed_roles = frozenset({User.Role.HOUSEKEEPING})


class IsCustomer(HasRole):
    allowed_roles = frozenset({User.Role.CUSTOMER})


class IsStaffRole(HasRole):
    allowed_roles = frozenset({
        User.Role.ADMIN,
        User.Role.MANAGER,
        User.Role.RECEPTIONIST,
        User.Role.HOUSEKEEPING,
    })


class IsAdminRole(IsAdmin):
    pass


class IsCustomerProfileOwner(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return request.user.role == User.Role.CUSTOMER and obj.user_id == request.user.id


class IsCustomerProfileStaff(HasRole):
    allowed_roles = frozenset({User.Role.ADMIN, User.Role.MANAGER, User.Role.RECEPTIONIST})
