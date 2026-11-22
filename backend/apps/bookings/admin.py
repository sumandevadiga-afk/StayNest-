from django.contrib import admin

from .models import Booking, QRToken


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "room", "check_in_date", "check_out_date", "status", "total_amount")
    list_filter = ("status", "check_in_date", "check_out_date")
    search_fields = ("customer__email", "room__room_number")


@admin.register(QRToken)
class QRTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "created_at", "expires_at", "used_at", "revoked_at")
    list_filter = ("expires_at", "used_at", "revoked_at")
    readonly_fields = ("token_hash", "created_at", "expires_at", "used_at", "revoked_at")
