from django.urls import path

from .views import AdminScopeView, CurrentUserView, LoginView, RegisterView, StaffScopeView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("staff-scope/", StaffScopeView.as_view(), name="staff_scope"),
    path("admin-scope/", AdminScopeView.as_view(), name="admin_scope"),
]
