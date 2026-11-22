import base64
import hashlib
import io
import secrets
from datetime import timedelta

import qrcode
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.rooms.models import Room

from .models import Booking, QRToken


def hash_qr_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_qr_token(booking):
    raw_token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(
        minutes=int(getattr(settings, "QR_TOKEN_EXPIRY_MINUTES", 15))
    )
    with transaction.atomic():
        QRToken.objects.select_for_update().filter(
            booking=booking,
            used_at__isnull=True,
            revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        token = QRToken.objects.create(
            booking=booking,
            token_hash=hash_qr_token(raw_token),
            expires_at=expires_at,
        )
    return token, raw_token


def qr_png_data_uri(raw_token):
    image = qrcode.make(raw_token)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def check_in_booking(booking_id):
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related("room").get(pk=booking_id)
        if booking.status in {Booking.Status.CANCELLED, Booking.Status.CHECKED_OUT, Booking.Status.NO_SHOW}:
            raise ValidationError({"booking": "This booking cannot be checked in."})
        if booking.status == Booking.Status.CHECKED_IN:
            raise ValidationError({"booking": "This booking is already checked in."})
        room = Room.objects.select_for_update().get(pk=booking.room_id)
        if room.status in {Room.Status.MAINTENANCE, Room.Status.INACTIVE}:
            raise ValidationError({"room": "This room cannot be used for check-in."})
        booking.status = Booking.Status.CHECKED_IN
        booking.save(update_fields=("status", "updated_at"))
        room.status = Room.Status.OCCUPIED
        room.save(update_fields=("status",))
        return booking


def check_out_booking(booking_id):
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related("room").get(pk=booking_id)
        if booking.status == Booking.Status.CANCELLED:
            raise ValidationError({"booking": "A cancelled booking cannot be checked out."})
        if booking.status == Booking.Status.CHECKED_OUT:
            raise ValidationError({"booking": "This booking is already checked out."})
        if booking.status != Booking.Status.CHECKED_IN:
            raise ValidationError({"booking": "Only checked-in bookings can be checked out."})
        room = Room.objects.select_for_update().get(pk=booking.room_id)
        booking.status = Booking.Status.CHECKED_OUT
        booking.save(update_fields=("status", "updated_at"))
        room.status = Room.Status.CLEANING
        room.save(update_fields=("status",))
        return booking
