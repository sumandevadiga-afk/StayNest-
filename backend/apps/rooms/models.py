from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class RoomType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    amenities = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        CLEANING = "CLEANING", "Cleaning"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        INACTIVE = "INACTIVE", "Inactive"

    room_number = models.CharField(max_length=20, unique=True)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    floor = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("room_number",)

    def __str__(self):
        return self.room_number
