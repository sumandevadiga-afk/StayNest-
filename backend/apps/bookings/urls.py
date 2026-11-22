from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AvailabilityView, BookingViewSet


router = DefaultRouter()
router.register("", BookingViewSet, basename="booking")

urlpatterns = [path("availability/", AvailabilityView.as_view(), name="booking-availability")] + router.urls
