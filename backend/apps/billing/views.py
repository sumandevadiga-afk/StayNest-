from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User

from .models import Invoice, Payment
from .permissions import BillingReadPermission, BillingStaffPermission, STAFF_ROLES
from .serializers import InvoiceSerializer, PaymentSerializer
from .services import update_invoice_status


class InvoiceViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.select_related("booking", "booking__customer").prefetch_related("items", "payments")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.CUSTOMER:
            return queryset.for_customer(self.request.user)
        if self.request.user.role in STAFF_ROLES:
            return queryset
        return queryset.none()

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [BillingReadPermission()]
        return [BillingStaffPermission()]

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.PAID:
            return Response({"detail": "Paid invoices cannot be voided."}, status=status.HTTP_400_BAD_REQUEST)
        invoice.status = Invoice.Status.VOID
        invoice.save(update_fields=("status",))
        return Response(self.get_serializer(invoice).data)


class PaymentViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.select_related("invoice", "invoice__booking", "invoice__booking__customer", "recorded_by")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.CUSTOMER:
            return queryset.filter(invoice__booking__customer=self.request.user)
        if self.request.user.role in STAFF_ROLES:
            return queryset
        return queryset.none()

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [BillingReadPermission()]
        return [BillingStaffPermission()]

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        with transaction.atomic():
            payment = get_object_or_404(Payment.objects.select_for_update(), pk=pk)
            if payment.status != Payment.Status.SUCCESSFUL:
                return Response({"detail": "Only successful payments can be refunded."}, status=status.HTTP_400_BAD_REQUEST)
            payment.status = Payment.Status.REFUNDED
            payment.paid_at = payment.paid_at or timezone.now()
            payment.save(update_fields=("status",))
            update_invoice_status(payment.invoice)
        return Response(self.get_serializer(payment).data)
