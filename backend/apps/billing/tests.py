from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.rooms.models import Room, RoomType

from .models import Invoice, Payment


class BillingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("billing-customer@example.com", "password", role=User.Role.CUSTOMER)
        self.other_customer = User.objects.create_user("other-billing@example.com", "password", role=User.Role.CUSTOMER)
        self.manager = User.objects.create_user("billing-manager@example.com", "password", role=User.Role.MANAGER)
        room_type = RoomType.objects.create(name="Billing Deluxe", base_price=Decimal("250.00"), capacity=2)
        room = Room.objects.create(room_number="BL101", room_type=room_type)
        self.booking = Booking.objects.create(
            customer=self.customer,
            room=room,
            check_in_date=date(2026, 12, 20),
            check_out_date=date(2026, 12, 22),
            guest_count=1,
            total_amount=Decimal("500.00"),
        )
        other_room = Room.objects.create(room_number="BL102", room_type=room_type)
        self.other_booking = Booking.objects.create(
            customer=self.other_customer,
            room=other_room,
            check_in_date=date(2026, 12, 23),
            check_out_date=date(2026, 12, 25),
            guest_count=1,
            total_amount=Decimal("400.00"),
        )

    def as_manager(self):
        self.client.force_authenticate(user=self.manager)

    def as_customer(self, user=None):
        self.client.force_authenticate(user=user or self.customer)

    def create_invoice(self, booking=None):
        self.as_manager()
        return self.client.post(
            "/api/billing/invoices/",
            {
                "booking": (booking or self.booking).id,
                "tax": "20.00",
                "discount": "10.00",
                "extra_items": [
                    {"description": "Breakfast", "quantity": 2, "unit_price": "25.00"},
                ],
            },
            format="json",
        )

    def test_invoice_totals_are_calculated_server_side(self):
        response = self.create_invoice()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice = Invoice.objects.get(pk=response.data["id"])
        self.assertEqual(invoice.subtotal, Decimal("550.00"))
        self.assertEqual(invoice.total, Decimal("560.00"))
        self.assertEqual(invoice.items.get(description="Breakfast").amount, Decimal("50.00"))
        self.assertEqual(response.data["status"], Invoice.Status.OPEN)

    def test_successful_and_failed_payments_update_status_safely(self):
        invoice_response = self.create_invoice()
        invoice_id = invoice_response.data["id"]
        self.as_manager()

        failed = self.client.post(
            "/api/billing/payments/",
            {"invoice": invoice_id, "amount": "100.00", "method": "DEMO_CASH", "outcome": "FAILED"},
            format="json",
        )
        successful = self.client.post(
            "/api/billing/payments/",
            {"invoice": invoice_id, "amount": "560.00", "method": "DEMO_CASH"},
            format="json",
        )

        self.assertEqual(failed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(successful.status_code, status.HTTP_201_CREATED)
        invoice = Invoice.objects.get(pk=invoice_id)
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertEqual(Payment.objects.get(pk=failed.data["id"]).status, Payment.Status.FAILED)

    def test_payment_over_balance_is_rejected(self):
        invoice_response = self.create_invoice()
        self.as_manager()

        response = self.client.post(
            "/api/billing/payments/",
            {"invoice": invoice_response.data["id"], "amount": "561.00", "method": "DEMO_CARD"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_only_view_owned_invoices_and_payments(self):
        own_invoice = self.create_invoice().data
        other_invoice = self.create_invoice(self.other_booking).data
        self.as_manager()
        payment = self.client.post(
            "/api/billing/payments/",
            {"invoice": own_invoice["id"], "amount": "50.00", "method": "DEMO_CASH"},
            format="json",
        ).data
        self.as_customer()

        invoices = self.client.get("/api/billing/invoices/")
        payments = self.client.get("/api/billing/payments/")
        other_detail = self.client.get(f"/api/billing/invoices/{other_invoice['id']}/")

        self.assertEqual(invoices.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in invoices.data}, {own_invoice["id"]})
        self.assertEqual(payments.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in payments.data}, {payment["id"]})
        self.assertEqual(other_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_successful_payments_are_analytics_eligible(self):
        invoice_response = self.create_invoice()
        self.as_manager()
        failed = self.client.post(
            "/api/billing/payments/",
            {"invoice": invoice_response.data["id"], "amount": "40.00", "method": "DEMO_TRANSFER", "outcome": "FAILED"},
            format="json",
        ).data
        successful = self.client.post(
            "/api/billing/payments/",
            {"invoice": invoice_response.data["id"], "amount": "60.00", "method": "DEMO_TRANSFER"},
            format="json",
        ).data

        self.assertEqual(Payment.objects.successful().successful_total(), Decimal("60.00"))
        self.client.post(f"/api/billing/payments/{successful['id']}/refund/", format="json")
        self.assertEqual(Payment.objects.successful().successful_total(), Decimal("0.00"))
        self.assertEqual(Payment.objects.get(pk=failed["id"]).status, Payment.Status.FAILED)
