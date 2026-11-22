from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Invoice, InvoiceItem, Payment


def update_invoice_status(invoice):
    if invoice.status == Invoice.Status.VOID:
        return invoice
    successful_total = invoice.payments.successful().successful_total()
    if successful_total >= invoice.total:
        invoice.status = Invoice.Status.PAID
    elif successful_total > 0:
        invoice.status = Invoice.Status.PARTIALLY_PAID
    else:
        invoice.status = Invoice.Status.OPEN
    invoice.save(update_fields=("status",))
    return invoice


def generate_invoice(booking, tax=Decimal("0.00"), discount=Decimal("0.00"), extra_items=None):
    extra_items = extra_items or []
    with transaction.atomic():
        booking = booking.__class__.objects.select_for_update().get(pk=booking.pk)
        if hasattr(booking, "invoice"):
            raise ValidationError({"booking": "This booking already has an invoice."})
        invoice = Invoice.objects.create(booking=booking, tax=tax, discount=discount)
        InvoiceItem.objects.create(
            invoice=invoice,
            description=f"Room charges - {booking.room.room_number}",
            quantity=1,
            unit_price=booking.total_amount,
        )
        for item in extra_items:
            InvoiceItem.objects.create(invoice=invoice, **item)
        subtotal = invoice.items.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total = subtotal + tax - discount
        if total < 0:
            raise ValidationError({"discount": "Discount cannot exceed subtotal plus tax."})
        invoice.subtotal = subtotal
        invoice.total = total
        invoice.save(update_fields=("subtotal", "total"))
        return invoice


def next_demo_reference():
    return f"DEMO-{uuid4().hex[:24].upper()}"


def record_demo_payment(invoice, amount, method, outcome, recorded_by):
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status == Invoice.Status.VOID:
            raise ValidationError({"invoice": "Void invoices cannot receive payments."})
        amount = Decimal(amount)
        successful_total = invoice.payments.successful().successful_total()
        if outcome == Payment.Status.SUCCESSFUL and amount > invoice.total - successful_total:
            raise ValidationError({"amount": "Payment exceeds the invoice balance."})
        payment = Payment.objects.create(
            invoice=invoice,
            amount=amount,
            method=method,
            status=outcome,
            reference=next_demo_reference(),
            paid_at=timezone.now() if outcome == Payment.Status.SUCCESSFUL else None,
            recorded_by=recorded_by,
        )
        update_invoice_status(invoice)
        return payment
