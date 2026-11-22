from rest_framework import serializers

from apps.bookings.models import Booking

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="customer.email", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "customer",
            "customer_email",
            "rating",
            "title",
            "comment",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "customer", "customer_email", "status", "created_at", "updated_at")

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None:
            booking = attrs.get("booking")
            if not booking:
                raise serializers.ValidationError({"booking": "A booking is required."})
            if booking.customer_id != request.user.id:
                raise serializers.ValidationError({"booking": "You may review only your own booking."})
            if booking.status != Booking.Status.CHECKED_OUT:
                raise serializers.ValidationError({"booking": "Reviews require a checked-out booking."})
            if Review.objects.filter(booking=booking).exists():
                raise serializers.ValidationError({"booking": "This booking already has a review."})
        return attrs

    def create(self, validated_data):
        return Review.objects.create(customer=self.context["request"].user, **validated_data)
