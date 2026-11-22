from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.bookings.models import Booking


class InvoiceQuerySet(models.QuerySet):
    def for_customer(self, user):
        return self.filter(booking__customer=user)


class Invoice(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="invoice")
    invoice_number = models.CharField(max_length=32, unique=True, editable=False)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    issued_at = models.DateTimeField(auto_now_add=True)

    objects = InvoiceQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"STN-{uuid4().hex[:20].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return self.description


class PaymentQuerySet(models.QuerySet):
    def successful(self):
        return self.filter(status=Payment.Status.SUCCESSFUL)

    def successful_total(self):
        from django.db.models import Sum

        return self.successful().aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


class Payment(models.Model):
    class Status(models.TextChoices):
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    class Method(models.TextChoices):
        DEMO_CASH = "DEMO_CASH", "Demo cash"
        DEMO_CARD = "DEMO_CARD", "Demo card"
        DEMO_TRANSFER = "DEMO_TRANSFER", "Demo transfer"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=30, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    reference = models.CharField(max_length=40, unique=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_payments")

    objects = PaymentQuerySet.as_manager()

    def __str__(self):
        return self.reference
