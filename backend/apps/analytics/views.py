from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAnalyticsManagerOrAdmin, IsAnalyticsStaff
from .serializers import (
    AnalyticsDateRangeSerializer,
    AnalyticsOverviewSerializer,
    OperationsAnalyticsSerializer,
)
from .services import calculate_analytics


class AnalyticsBaseView(APIView):
    def get_date_range(self, request):
        serializer = AnalyticsDateRangeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data.get("start_date"), serializer.validated_data.get("end_date")


class AnalyticsOverviewView(AnalyticsBaseView):
    permission_classes = (IsAnalyticsManagerOrAdmin,)

    def get(self, request):
        start_date, end_date = self.get_date_range(request)
        data = calculate_analytics(start_date, end_date)
        return Response(AnalyticsOverviewSerializer(data).data)


class AnalyticsOperationsView(AnalyticsBaseView):
    permission_classes = (IsAnalyticsStaff,)

    def get(self, request):
        start_date, end_date = self.get_date_range(request)
        data = calculate_analytics(start_date, end_date)
        return Response(OperationsAnalyticsSerializer({
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "booking_count": data["booking_count"],
            "check_in_count": data["check_in_count"],
            "check_out_count": data["check_out_count"],
        }).data)
