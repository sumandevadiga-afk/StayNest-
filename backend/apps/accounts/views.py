from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminRole, IsStaffRole
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer


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
