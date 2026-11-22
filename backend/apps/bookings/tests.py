from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.rooms.models import Room, RoomType

from .models import Booking


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
