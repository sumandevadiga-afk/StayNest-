from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminRole, IsCustomer, IsCustomerProfileStaff, IsStaffRole
from .serializers import CustomerProfileSerializer, LoginSerializer, RegisterSerializer, UserSerializer
from .models import CustomerProfile, User


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = (AllowAny,)


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class StaffScopeView(APIView):
    permission_classes = (IsStaffRole,)

    def get(self, request):
        return Response({"status": "ok", "scope": "staff", "role": request.user.role})


class AdminScopeView(APIView):
    permission_classes = (IsAdminRole,)

    def get(self, request):
        return Response({"status": "ok", "scope": "admin", "role": request.user.role})


class CustomerProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = (IsCustomer,)

    def get_object(self):
        return CustomerProfile.objects.get(user=self.request.user)


class CustomerProfileOperationsView(generics.ListAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = (IsCustomerProfileStaff,)
    queryset = CustomerProfile.objects.select_related("user").all()
