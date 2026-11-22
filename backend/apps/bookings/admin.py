from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "room", "check_in_date", "check_out_date", "status", "total_amount")
    list_filter = ("status", "check_in_date", "check_out_date")
    search_fields = ("customer__email", "room__room_number")
