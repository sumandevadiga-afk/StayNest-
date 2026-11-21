from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.accounts.models import User

from .models import Room, RoomType
from .permissions import IsManagerOrAdmin
from .serializers import RoomSerializer, RoomTypeSerializer


class RoomTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RoomTypeSerializer
    queryset = RoomType.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated or self.request.user.role not in {
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.RECEPTIONIST,
            User.Role.HOUSEKEEPING,
        }:
            return queryset.filter(active=True)
        return queryset

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsManagerOrAdmin()]


class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    queryset = Room.objects.select_related("room_type").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated or self.request.user.role not in {
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.RECEPTIONIST,
            User.Role.HOUSEKEEPING,
        }:
            return queryset.filter(status=Room.Status.AVAILABLE, room_type__active=True)
        return queryset

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsManagerOrAdmin()]
