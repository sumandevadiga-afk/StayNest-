from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AvailabilityView,
    BookingCheckInView,
    BookingCheckOutView,
    BookingQRCodeView,
    BookingViewSet,
    QRTokenConsumeView,
    QRTokenRevokeView,
)


router = DefaultRouter()
router.register("", BookingViewSet, basename="booking")

urlpatterns = [
    path("availability/", AvailabilityView.as_view(), name="booking-availability"),
    path("qr/consume/", QRTokenConsumeView.as_view(), name="qr-consume"),
    path("qr/<int:pk>/revoke/", QRTokenRevokeView.as_view(), name="qr-revoke"),
    path("<int:pk>/qr/", BookingQRCodeView.as_view(), name="booking-qr"),
    path("<int:pk>/check-in/", BookingCheckInView.as_view(), name="booking-check-in"),
    path("<int:pk>/check-out/", BookingCheckOutView.as_view(), name="booking-check-out"),
] + router.urls
