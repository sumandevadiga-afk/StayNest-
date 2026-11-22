from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.rooms.models import Room
from apps.rooms.serializers import RoomSerializer

from .models import Booking
from .permissions import BookingAccessPermission, BookingWritePermission, STAFF_ROLES
from .serializers import AvailabilityQuerySerializer, BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    queryset = Booking.objects.select_related("customer", "room", "room__room_type").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.CUSTOMER:
            return queryset.filter(customer=self.request.user)
        if self.request.user.role in STAFF_ROLES:
            return queryset
        return queryset.none()

    def get_permissions(self):
        if self.action == "create":
            return [BookingAccessPermission()]
        if self.action in {"list", "retrieve"}:
            return [BookingAccessPermission()]
        return [BookingWritePermission()]


class AvailabilityView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=False)
        if query.errors:
            return Response(query.errors, status=status.HTTP_400_BAD_REQUEST)

        check_in = query.validated_data["check_in_date"]
        check_out = query.validated_data["check_out_date"]
        rooms = Room.objects.select_related("room_type").filter(
            room_type__active=True,
        ).exclude(
            status__in=[Room.Status.MAINTENANCE, Room.Status.INACTIVE],
        ).exclude(
            bookings__status__in=[
                booking_status
                for booking_status in Booking.Status.values
                if booking_status != Booking.Status.CANCELLED
            ],
            bookings__check_in_date__lt=check_out,
            bookings__check_out_date__gt=check_in,
        ).distinct()
        return Response({
            "check_in_date": check_in,
            "check_out_date": check_out,
            "rooms": RoomSerializer(rooms, many=True).data,
        })
