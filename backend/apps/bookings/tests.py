from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.rooms.models import Room, RoomType

from .models import Booking, QRToken
from .services import hash_qr_token, issue_qr_token


class BookingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("booking-customer@example.com", "password", role=User.Role.CUSTOMER)
        self.other_customer = User.objects.create_user("other-booking@example.com", "password", role=User.Role.CUSTOMER)
        self.manager = User.objects.create_user("booking-manager@example.com", "password", role=User.Role.MANAGER)
        self.room_type = RoomType.objects.create(name="Booking Deluxe", base_price=Decimal("150.00"), capacity=2)
        self.room = Room.objects.create(room_number="B101", room_type=self.room_type, floor=1)
        self.maintenance_room = Room.objects.create(
            room_number="B102",
            room_type=self.room_type,
            floor=1,
            status=Room.Status.MAINTENANCE,
        )
        self.start = date(2026, 12, 10)

    def payload(self, room=None, check_in=None, check_out=None, guest_count=2):
        return {
            "room": (room or self.room).id,
            "check_in_date": (check_in or self.start).isoformat(),
            "check_out_date": (check_out or self.start + timedelta(days=2)).isoformat(),
            "guest_count": guest_count,
            "total_amount": "300.00",
            "special_requests": "Late arrival",
        }

    def as_customer(self, user=None):
        self.client.force_authenticate(user=user or self.customer)

    def create_booking(self, user=None, **kwargs):
        self.as_customer(user)
        return self.client.post("/api/bookings/", self.payload(**kwargs), format="json")

    def test_successful_booking(self):
        response = self.create_booking()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(pk=response.data["id"])
        self.assertEqual(booking.customer, self.customer)
        self.assertEqual(booking.room, self.room)
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_invalid_dates_are_rejected(self):
        response = self.create_booking(check_in=self.start, check_out=self.start)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("check_out_date", response.data)

    def test_capacity_validation(self):
        response = self.create_booking(guest_count=3)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("guest_count", response.data)

    def test_maintenance_room_is_rejected(self):
        response = self.create_booking(room=self.maintenance_room)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", response.data)

    def test_overlapping_booking_is_rejected(self):
        first = self.create_booking()
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.create_booking(user=self.other_customer, check_in=self.start + timedelta(days=1))

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("room", second.data)

    def test_back_to_back_bookings_are_allowed(self):
        first = self.create_booking()
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.create_booking(
            user=self.other_customer,
            check_in=self.start + timedelta(days=2),
            check_out=self.start + timedelta(days=4),
        )

        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

    def test_cancelled_booking_does_not_block_availability(self):
        booking = Booking.objects.create(
            customer=self.customer,
            room=self.room,
            check_in_date=self.start,
            check_out_date=self.start + timedelta(days=2),
            guest_count=1,
            total_amount=Decimal("100.00"),
            status=Booking.Status.CANCELLED,
        )

        response = self.client.get(
            "/api/bookings/availability/",
            {"check_in_date": self.start.isoformat(), "check_out_date": (self.start + timedelta(days=2)).isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.room.room_number, {room["room_number"] for room in response.data["rooms"]})
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_customer_data_isolation(self):
        other_booking = self.create_booking(user=self.other_customer)
        self.as_customer(self.customer)

        list_response = self.client.get("/api/bookings/")
        detail_response = self.client.get(f"/api/bookings/{other_booking.data['id']}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data, [])
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_view_all_bookings(self):
        self.create_booking(user=self.customer)
        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/bookings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class ReceptionOperationsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("qr-customer@example.com", "password", role=User.Role.CUSTOMER)
        self.receptionist = User.objects.create_user("qr-reception@example.com", "password", role=User.Role.RECEPTIONIST)
        self.room_type = RoomType.objects.create(name="Reception Deluxe", base_price=Decimal("180.00"), capacity=2)
        self.room = Room.objects.create(room_number="R101", room_type=self.room_type, floor=1)

    def make_booking(self, status=Booking.Status.CONFIRMED, room=None):
        return Booking.objects.create(
            customer=self.customer,
            room=room or self.room,
            check_in_date=date(2026, 12, 10),
            check_out_date=date(2026, 12, 12),
            guest_count=1,
            status=status,
            total_amount=Decimal("360.00"),
        )

    def as_receptionist(self):
        self.client.force_authenticate(user=self.receptionist)

    def test_valid_qr_token_checks_in_booking_and_occupies_room(self):
        booking = self.make_booking()
        _, raw_token = issue_qr_token(booking)
        self.as_receptionist()

        response = self.client.post(
            "/api/bookings/qr/consume/",
            {"token": raw_token, "action": "check_in"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CHECKED_IN)
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)

    def test_invalid_expired_revoked_and_reused_tokens_are_rejected(self):
        booking = self.make_booking()
        self.as_receptionist()

        invalid = self.client.post("/api/bookings/qr/consume/", {"token": "invalid", "action": "check_in"}, format="json")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        _, expired_raw = issue_qr_token(booking)
        expired = QRToken.objects.get(token_hash=hash_qr_token(expired_raw))
        expired.expires_at = timezone.now() - timedelta(minutes=1)
        expired.save(update_fields=("expires_at",))
        expired_response = self.client.post("/api/bookings/qr/consume/", {"token": expired_raw, "action": "check_in"}, format="json")
        self.assertEqual(expired_response.status_code, status.HTTP_400_BAD_REQUEST)

        _, revoked_raw = issue_qr_token(booking)
        revoked = QRToken.objects.get(token_hash=hash_qr_token(revoked_raw))
        revoked.revoked_at = timezone.now()
        revoked.save(update_fields=("revoked_at",))
        revoked_response = self.client.post("/api/bookings/qr/consume/", {"token": revoked_raw, "action": "check_in"}, format="json")
        self.assertEqual(revoked_response.status_code, status.HTTP_400_BAD_REQUEST)

        _, reusable_raw = issue_qr_token(booking)
        first_use = self.client.post("/api/bookings/qr/consume/", {"token": reusable_raw, "action": "check_in"}, format="json")
        second_use = self.client.post("/api/bookings/qr/consume/", {"token": reusable_raw, "action": "check_in"}, format="json")
        self.assertEqual(first_use.status_code, status.HTTP_200_OK)
        self.assertEqual(second_use.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_can_view_own_qr_code_without_raw_token_response(self):
        booking = self.make_booking()
        self.client.force_authenticate(user=self.customer)

        response = self.client.get(f"/api/bookings/{booking.id}/qr/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["qr_code"].startswith("data:image/png;base64,"))
        self.assertNotIn("token_hash", response.data)

    def test_unauthorized_check_in_is_rejected(self):
        booking = self.make_booking()
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(f"/api/bookings/{booking.id}/check-in/", format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancelled_booking_cannot_check_in(self):
        booking = self.make_booking(status=Booking.Status.CANCELLED)
        self.as_receptionist()

        response = self.client.post(f"/api/bookings/{booking.id}/check-in/", format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_check_in_and_check_out_update_room_status(self):
        booking = self.make_booking()
        self.as_receptionist()

        check_in = self.client.post(f"/api/bookings/{booking.id}/check-in/", format="json")
        self.assertEqual(check_in.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)

        check_out = self.client.post(f"/api/bookings/{booking.id}/check-out/", format="json")
        self.assertEqual(check_out.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CHECKED_OUT)
        self.assertEqual(self.room.status, Room.Status.CLEANING)
