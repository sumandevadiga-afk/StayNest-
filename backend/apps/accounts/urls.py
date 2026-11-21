from django.urls import path

from .views import (
    AdminScopeView,
    CurrentUserView,
    CustomerProfileMeView,
    CustomerProfileOperationsView,
    LoginView,
    RegisterView,
    StaffScopeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("staff-scope/", StaffScopeView.as_view(), name="staff_scope"),
    path("admin-scope/", AdminScopeView.as_view(), name="admin_scope"),
    path("profile/", CustomerProfileMeView.as_view(), name="customer_profile_me"),
    path("profiles/", CustomerProfileOperationsView.as_view(), name="customer_profiles_operations"),
]
