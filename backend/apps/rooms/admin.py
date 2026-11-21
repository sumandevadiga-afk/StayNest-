from django.contrib import admin

from .models import Room, RoomType


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "base_price", "capacity", "active")
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "floor", "status")
    list_filter = ("status", "floor")
    search_fields = ("room_number", "room_type__name")
