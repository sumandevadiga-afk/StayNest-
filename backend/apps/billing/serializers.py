from decimal import Decimal

from rest_framework import serializers

from apps.bookings.models import Booking

from .models import Invoice, InvoiceItem, Payment
from .services import generate_invoice, record_demo_payment


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ("id", "description", "quantity", "unit_price", "amount")
        read_only_fields = ("id", "amount")

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be positive.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    extra_items = InvoiceItemSerializer(many=True, write_only=True, required=False)
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())

    class Meta:
        model = Invoice
        fields = (
            "id",
            "booking",
            "invoice_number",
            "subtotal",
            "tax",
            "discount",
            "total",
            "status",
            "issued_at",
            "items",
            "extra_items",
        )
        read_only_fields = ("id", "invoice_number", "subtotal", "total", "status", "issued_at", "items")

    def validate_tax(self, value):
        if value < 0:
            raise serializers.ValidationError("Tax cannot be negative.")
        return value

    def validate_discount(self, value):
        if value < 0:
            raise serializers.ValidationError("Discount cannot be negative.")
        return value

    def create(self, validated_data):
        extra_items = validated_data.pop("extra_items", [])
        return generate_invoice(
            validated_data["booking"],
            tax=validated_data.get("tax", Decimal("0.00")),
            discount=validated_data.get("discount", Decimal("0.00")),
            extra_items=extra_items,
        )


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    outcome = serializers.ChoiceField(
        choices=(Payment.Status.SUCCESSFUL, Payment.Status.FAILED),
        write_only=True,
        default=Payment.Status.SUCCESSFUL,
    )

    class Meta:
        model = Payment
        fields = (
            "id",
            "invoice",
            "invoice_number",
            "amount",
            "method",
            "status",
            "outcome",
            "reference",
            "paid_at",
            "recorded_by",
        )
        read_only_fields = ("id", "invoice_number", "status", "reference", "paid_at", "recorded_by")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be positive.")
        return value

    def create(self, validated_data):
        outcome = validated_data.pop("outcome", Payment.Status.SUCCESSFUL)
        return record_demo_payment(
            invoice=validated_data["invoice"],
            amount=validated_data["amount"],
            method=validated_data["method"],
            outcome=outcome,
            recorded_by=self.context["request"].user,
        )
