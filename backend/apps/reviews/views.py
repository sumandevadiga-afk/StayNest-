from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.models import User

from .models import Review
from .permissions import IsCustomer, IsManagerOrAdmin, IsPendingReviewOwner
from .serializers import ReviewSerializer


class ReviewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related("customer", "booking").all()

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(status=Review.Status.APPROVED)
        if self.request.user.role in {User.Role.ADMIN, User.Role.MANAGER}:
            return queryset
        if self.request.user.role == User.Role.CUSTOMER:
            return queryset.filter(status=Review.Status.APPROVED) | queryset.filter(customer=self.request.user)
        return queryset.filter(status=Review.Status.APPROVED)

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        if self.action == "create":
            return [IsCustomer()]
        if self.action == "moderate":
            return [IsManagerOrAdmin()]
        return [IsPendingReviewOwner()]

    @action(detail=True, methods=["post"])
    def moderate(self, request, pk=None):
        review = self.get_object()
        new_status = request.data.get("status")
        if new_status not in {Review.Status.APPROVED, Review.Status.HIDDEN}:
            return Response({"status": "Use APPROVED or HIDDEN."}, status=status.HTTP_400_BAD_REQUEST)
        review.status = new_status
        review.save(update_fields=("status", "updated_at"))
        return Response(self.get_serializer(review).data)
