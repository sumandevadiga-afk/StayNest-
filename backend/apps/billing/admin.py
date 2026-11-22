from django.contrib import admin

from .models import Invoice, InvoiceItem, Payment


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("amount",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "booking", "total", "status", "issued_at")
    list_filter = ("status", "issued_at")
    search_fields = ("invoice_number", "booking__customer__email")
    inlines = (InvoiceItemInline,)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "invoice", "amount", "method", "status", "paid_at", "recorded_by")
    list_filter = ("status", "method", "paid_at")
    search_fields = ("reference", "invoice__invoice_number", "invoice__booking__customer__email")
    readonly_fields = ("reference", "paid_at", "recorded_by")
