from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.rooms.models import Room
from apps.rooms.serializers import RoomSerializer

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.CUSTOMER),
        required=False,
    )
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    room_detail = RoomSerializer(source="room", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "customer",
            "customer_email",
            "room",
            "room_detail",
            "check_in_date",
            "check_out_date",
            "guest_count",
            "status",
            "total_amount",
            "special_requests",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "customer_email", "room_detail", "created_at", "updated_at")

    def validate(self, attrs):
        check_in = attrs.get("check_in_date", getattr(self.instance, "check_in_date", None))
        check_out = attrs.get("check_out_date", getattr(self.instance, "check_out_date", None))
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError({"check_out_date": "Check-out must be after check-in."})

        room = attrs.get("room", getattr(self.instance, "room", None))
        guest_count = attrs.get("guest_count", getattr(self.instance, "guest_count", None))
        if room and room.status in {Room.Status.MAINTENANCE, Room.Status.INACTIVE}:
            raise serializers.ValidationError({"room": "This room cannot be booked in its current status."})
        if room and guest_count and guest_count > room.room_type.capacity:
            raise serializers.ValidationError({"guest_count": "Guest count exceeds room capacity."})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        if request.user.role == User.Role.CUSTOMER:
            validated_data["customer"] = request.user
        elif "customer" not in validated_data:
            raise serializers.ValidationError({"customer": "A customer is required."})

        room_id = validated_data["room"].pk
        with transaction.atomic():
            room = Room.objects.select_for_update().select_related("room_type").get(pk=room_id)
            self._validate_locked_booking(room, validated_data)
            conflict = Booking.objects.filter(room=room).exclude(status=Booking.Status.CANCELLED).filter(
                check_in_date__lt=validated_data["check_out_date"],
                check_out_date__gt=validated_data["check_in_date"],
            ).exists()
            if conflict:
                raise serializers.ValidationError({"room": "This room is already booked for the selected dates."})
            validated_data["room"] = room
            return Booking.objects.create(**validated_data)

    def _validate_locked_booking(self, room, validated_data):
        if room.status in {Room.Status.MAINTENANCE, Room.Status.INACTIVE}:
            raise serializers.ValidationError({"room": "This room cannot be booked in its current status."})
        if validated_data["guest_count"] > room.room_type.capacity:
            raise serializers.ValidationError({"guest_count": "Guest count exceeds room capacity."})


class AvailabilityQuerySerializer(serializers.Serializer):
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["check_out_date"] <= attrs["check_in_date"]:
            raise serializers.ValidationError({"check_out_date": "Check-out must be after check-in."})
        return attrs
