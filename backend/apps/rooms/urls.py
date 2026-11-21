from rest_framework.routers import DefaultRouter

from .views import RoomTypeViewSet, RoomViewSet


router = DefaultRouter()
router.register("types", RoomTypeViewSet, basename="room-type")
router.register("", RoomViewSet, basename="room")

urlpatterns = router.urls
