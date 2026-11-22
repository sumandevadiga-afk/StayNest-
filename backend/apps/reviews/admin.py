from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "customer", "rating", "status", "created_at", "updated_at")
    list_filter = ("status", "rating", "created_at")
    search_fields = ("customer__email", "booking__id", "title", "comment")
