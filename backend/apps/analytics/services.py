from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth

from apps.billing.models import Payment
from apps.bookings.models import Booking
from apps.rooms.models import Room, RoomType


ZERO = Decimal("0.00")


def in_date_range(queryset, field, start_date, end_date):
    if start_date:
        queryset = queryset.filter(**{f"{field}__date__gte": start_date})
    if end_date:
        queryset = queryset.filter(**{f"{field}__date__lte": end_date})
    return queryset


def booking_date_range(queryset, field, start_date, end_date):
    if start_date:
        queryset = queryset.filter(**{f"{field}__gte": start_date})
    if end_date:
        queryset = queryset.filter(**{f"{field}__lte": end_date})
    return queryset


def calculate_analytics(start_date=None, end_date=None):
    bookings = Booking.objects.select_related("room", "room__room_type")
    if start_date:
        bookings = bookings.filter(check_out_date__gt=start_date)
    if end_date:
        bookings = bookings.filter(check_in_date__lte=end_date)
    bookings = bookings.exclude(status=Booking.Status.NO_SHOW)

    payment_queryset = Payment.objects.successful().select_related(
        "invoice__booking__room__room_type",
    )
    payment_queryset = in_date_range(payment_queryset, "paid_at", start_date, end_date)
    total_revenue = payment_queryset.aggregate(total=Sum("amount"))["total"] or ZERO

    monthly_rows = payment_queryset.annotate(month=TruncMonth("paid_at")).values("month").annotate(
        revenue=Sum("amount"),
    ).order_by("month")
    monthly_revenue = [
        {"month": row["month"].strftime("%Y-%m"), "revenue": row["revenue"] or ZERO}
        for row in monthly_rows
    ]

    booking_count = bookings.count()
    cancelled_count = bookings.filter(status=Booking.Status.CANCELLED).count()
    cancellation_rate = (Decimal(cancelled_count) / booking_count * 100) if booking_count else ZERO

    range_start = start_date or (bookings.order_by("check_in_date").values_list("check_in_date", flat=True).first())
    range_end = end_date or (bookings.order_by("-check_out_date").values_list("check_out_date", flat=True).first())
    occupancy_rate = calculate_occupancy(bookings, range_start, range_end)

    performance = []
    for room_type in RoomType.objects.all().order_by("name"):
        type_bookings = bookings.filter(room__room_type=room_type)
        type_payments = payment_queryset.filter(invoice__booking__room__room_type=room_type)
        performance.append({
            "room_type": room_type.name,
            "room_count": room_type.rooms.count(),
            "booking_count": type_bookings.count(),
            "successful_revenue": type_payments.aggregate(total=Sum("amount"))["total"] or ZERO,
        })

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_successful_revenue": total_revenue,
        "monthly_revenue": monthly_revenue,
        "booking_count": booking_count,
        "occupancy_rate": occupancy_rate,
        "cancellation_rate": cancellation_rate,
        "room_type_performance": performance,
        "average_review_rating": None,
        "check_in_count": booking_date_range(bookings, "check_in_date", start_date, end_date).filter(
            status__in=[Booking.Status.CHECKED_IN, Booking.Status.CHECKED_OUT],
        ).count(),
        "check_out_count": booking_date_range(bookings, "check_out_date", start_date, end_date).filter(
            status=Booking.Status.CHECKED_OUT,
        ).count(),
    }


def calculate_occupancy(bookings, range_start, range_end):
    if not range_start or not range_end or range_end <= range_start:
        return ZERO
    active_room_count = Room.objects.exclude(status=Room.Status.INACTIVE).count()
    total_nights = (range_end - range_start).days
    if not active_room_count or not total_nights:
        return ZERO
    occupied_nights = 0
    for booking in bookings.exclude(status=Booking.Status.CANCELLED):
        occupied_start = max(booking.check_in_date, range_start)
        occupied_end = min(booking.check_out_date, range_end)
        occupied_nights += max((occupied_end - occupied_start).days, 0)
    return (Decimal(occupied_nights) / Decimal(active_room_count * total_nights) * 100).quantize(Decimal("0.01"))
