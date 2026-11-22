from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.rooms.models import Room
from apps.rooms.serializers import RoomSerializer

from .models import Booking, QRToken
from .permissions import (
    BookingAccessPermission,
    BookingOwnerOrReceptionPermission,
    BookingWritePermission,
    ReceptionOperationsPermission,
    STAFF_ROLES,
)
from .serializers import AvailabilityQuerySerializer, BookingSerializer, QRTokenConsumeSerializer, QRTokenSerializer
from .services import check_in_booking, check_out_booking, hash_qr_token, issue_qr_token, qr_png_data_uri


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


class BookingQRCodeView(APIView):
    permission_classes = (BookingOwnerOrReceptionPermission,)

    def get(self, request, pk):
        booking = Booking.objects.select_related("customer", "room").filter(pk=pk).first()
        if not booking:
            raise NotFound("Booking not found.")
        if request.user.role not in STAFF_ROLES and booking.customer_id != request.user.id:
            raise NotFound("Booking not found.")
        token, raw_token = issue_qr_token(booking)
        return Response({
            "booking_id": booking.id,
            "qr_code": qr_png_data_uri(raw_token),
            "expires_at": token.expires_at,
            "token": QRTokenSerializer(token).data,
        })


class BookingCheckInView(APIView):
    permission_classes = (ReceptionOperationsPermission,)

    def post(self, request, pk):
        booking = check_in_booking(pk)
        return Response(BookingSerializer(booking, context={"request": request}).data)


class BookingCheckOutView(APIView):
    permission_classes = (ReceptionOperationsPermission,)

    def post(self, request, pk):
        booking = check_out_booking(pk)
        return Response(BookingSerializer(booking, context={"request": request}).data)


class QRTokenConsumeView(APIView):
    permission_classes = (ReceptionOperationsPermission,)

    def post(self, request):
        serializer = QRTokenConsumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        digest = hash_qr_token(serializer.validated_data["token"])
        with transaction.atomic():
            token = QRToken.objects.select_for_update().select_related("booking").filter(token_hash=digest).first()
            if not token:
                raise ValidationError({"token": "Invalid QR token."})
            now = timezone.now()
            if token.revoked_at:
                raise ValidationError({"token": "This QR token has been revoked."})
            if token.used_at:
                raise ValidationError({"token": "This QR token has already been used."})
            if token.expires_at <= now:
                raise ValidationError({"token": "This QR token has expired."})
            action = serializer.validated_data["action"]
            booking = check_in_booking(token.booking_id) if action == "check_in" else check_out_booking(token.booking_id)
            token.used_at = now
            token.save(update_fields=("used_at",))
        return Response({"booking": BookingSerializer(booking, context={"request": request}).data})


class QRTokenRevokeView(APIView):
    permission_classes = (ReceptionOperationsPermission,)

    def post(self, request, pk):
        token = QRToken.objects.filter(pk=pk).first()
        if not token:
            raise NotFound("QR token not found.")
        token.revoked_at = timezone.now()
        token.save(update_fields=("revoked_at",))
        return Response(QRTokenSerializer(token).data)
