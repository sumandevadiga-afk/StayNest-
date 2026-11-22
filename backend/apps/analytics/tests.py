from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.billing.models import Invoice, Payment
from apps.bookings.models import Booking
from apps.rooms.models import Room, RoomType


class AnalyticsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("analytics-admin@example.com", "password", role=User.Role.ADMIN)
        self.manager = User.objects.create_user("analytics-manager@example.com", "password", role=User.Role.MANAGER)
        self.receptionist = User.objects.create_user("analytics-reception@example.com", "password", role=User.Role.RECEPTIONIST)
        self.customer = User.objects.create_user("analytics-customer@example.com", "password", role=User.Role.CUSTOMER)
        self.room_type = RoomType.objects.create(name="Analytics Deluxe", base_price=Decimal("200.00"), capacity=2)
        self.room = Room.objects.create(room_number="AN101", room_type=self.room_type)
        self.booking = Booking.objects.create(
            customer=self.customer,
            room=self.room,
            check_in_date=date(2026, 1, 10),
            check_out_date=date(2026, 1, 12),
            guest_count=1,
            status=Booking.Status.CHECKED_OUT,
            total_amount=Decimal("400.00"),
        )
        self.invoice = Invoice.objects.create(
            booking=self.booking,
            subtotal=Decimal("400.00"),
            total=Decimal("400.00"),
        )

    def make_payment(self, amount, status_value, paid_at):
        return Payment.objects.create(
            invoice=self.invoice,
            amount=amount,
            method=Payment.Method.DEMO_CASH,
            status=status_value,
            reference=f"TEST-{amount}-{status_value}",
            paid_at=paid_at,
            recorded_by=self.manager,
        )

    def test_successful_payment_is_included_and_failed_refunded_are_excluded(self):
        self.make_payment(Decimal("100.00"), Payment.Status.SUCCESSFUL, datetime(2026, 1, 11, tzinfo=dt_timezone.utc))
        self.make_payment(Decimal("50.00"), Payment.Status.FAILED, datetime(2026, 1, 11, tzinfo=dt_timezone.utc))
        self.make_payment(Decimal("25.00"), Payment.Status.REFUNDED, datetime(2026, 1, 11, tzinfo=dt_timezone.utc))
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/analytics/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_successful_revenue"], "100.00")

    def test_date_filtering_limits_revenue(self):
        self.make_payment(Decimal("100.00"), Payment.Status.SUCCESSFUL, datetime(2026, 1, 11, tzinfo=dt_timezone.utc))
        self.make_payment(Decimal("80.00"), Payment.Status.SUCCESSFUL, datetime(2026, 2, 11, tzinfo=dt_timezone.utc))
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/analytics/overview/?start_date=2026-02-01&end_date=2026-02-28")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_successful_revenue"], "80.00")

    def test_role_permissions(self):
        self.client.force_authenticate(user=self.customer)
        self.assertEqual(self.client.get("/api/analytics/overview/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get("/api/analytics/operations/").status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(user=self.receptionist)
        self.assertEqual(self.client.get("/api/analytics/overview/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get("/api/analytics/operations/").status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=self.manager)
        self.assertEqual(self.client.get("/api/analytics/overview/").status_code, status.HTTP_200_OK)

    def test_empty_datasets_return_safe_values(self):
        Payment.objects.all().delete()
        Invoice.objects.all().delete()
        Booking.objects.all().delete()
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/analytics/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_successful_revenue"], "0.00")
        self.assertEqual(response.data["booking_count"], 0)
        self.assertEqual(response.data["monthly_revenue"], [])
        self.assertEqual(response.data["cancellation_rate"], "0.00")
