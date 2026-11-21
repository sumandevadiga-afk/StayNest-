from rest_framework import serializers

from .models import Room, RoomType


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = (
            "id",
            "name",
            "description",
            "base_price",
            "capacity",
            "amenities",
            "active",
        )

    def validate_base_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Base price must be positive.")
        return value

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be positive.")
        return value


class RoomSerializer(serializers.ModelSerializer):
    room_type_name = serializers.CharField(source="room_type.name", read_only=True)

    class Meta:
        model = Room
        fields = ("id", "room_number", "room_type", "room_type_name", "floor", "status", "notes")
