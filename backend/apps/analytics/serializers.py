from rest_framework import serializers


class AnalyticsDateRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get("start_date") and attrs.get("end_date") and attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs


class MonthlyRevenueSerializer(serializers.Serializer):
    month = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class RoomTypePerformanceSerializer(serializers.Serializer):
    room_type = serializers.CharField()
    room_count = serializers.IntegerField()
    booking_count = serializers.IntegerField()
    successful_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class AnalyticsOverviewSerializer(serializers.Serializer):
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    total_successful_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    monthly_revenue = MonthlyRevenueSerializer(many=True)
    booking_count = serializers.IntegerField()
    occupancy_rate = serializers.DecimalField(max_digits=7, decimal_places=2)
    cancellation_rate = serializers.DecimalField(max_digits=7, decimal_places=2)
    room_type_performance = RoomTypePerformanceSerializer(many=True)
    average_review_rating = serializers.DecimalField(max_digits=4, decimal_places=2, allow_null=True)
    check_in_count = serializers.IntegerField()
    check_out_count = serializers.IntegerField()


class OperationsAnalyticsSerializer(serializers.Serializer):
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)
    booking_count = serializers.IntegerField()
    check_in_count = serializers.IntegerField()
    check_out_count = serializers.IntegerField()
