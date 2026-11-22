from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.rooms.models import Room, RoomType

from .models import Review


class ReviewAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user("review-customer@example.com", "password", role=User.Role.CUSTOMER)
        self.other_customer = User.objects.create_user("review-other@example.com", "password", role=User.Role.CUSTOMER)
        self.manager = User.objects.create_user("review-manager@example.com", "password", role=User.Role.MANAGER)
        self.admin = User.objects.create_user("review-admin@example.com", "password", role=User.Role.ADMIN)
        room_type = RoomType.objects.create(name="Review Deluxe", base_price=Decimal("200.00"), capacity=2)
        self.room = Room.objects.create(room_number="RV101", room_type=room_type)
        self.checked_out_booking = self.make_booking(self.customer, Booking.Status.CHECKED_OUT)
        self.pending_booking = self.make_booking(self.customer, Booking.Status.CONFIRMED, "RV102")

    def make_booking(self, customer, booking_status, room_number=None):
        room = self.room if room_number is None else Room.objects.create(room_number=room_number, room_type=self.room.room_type)
        return Booking.objects.create(
            customer=customer,
            room=room,
            check_in_date=date(2026, 1, 10),
            check_out_date=date(2026, 1, 12),
            guest_count=1,
            status=booking_status,
            total_amount=Decimal("400.00"),
        )

    def submit_review(self, booking=None, customer=None, rating=5):
        self.client.force_authenticate(user=customer or self.customer)
        return self.client.post(
            "/api/reviews/",
            {"booking": (booking or self.checked_out_booking).id, "rating": rating, "title": "Great stay", "comment": "Very comfortable."},
            format="json",
        )

    def test_verified_stay_review(self):
        response = self.submit_review()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Review.Status.PENDING)

    def test_unverified_customer_rejected(self):
        response = self.submit_review(self.pending_booking)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_customer_rejected(self):
        response = self.submit_review(customer=self.other_customer)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_review_rejected(self):
        self.submit_review()
        response = self.submit_review()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rating_validation(self):
        response = self.submit_review(rating=6)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_moderation_permissions_and_pending_edit(self):
        review = self.submit_review().data
        self.client.force_authenticate(user=self.customer)
        edit = self.client.patch(f"/api/reviews/{review['id']}/", {"title": "Updated"}, format="json")
        self.assertEqual(edit.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=self.manager)
        moderate = self.client.post(f"/api/reviews/{review['id']}/moderate/", {"status": "APPROVED"}, format="json")
        self.assertEqual(moderate.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(user=self.customer)
        edit_approved = self.client.patch(f"/api/reviews/{review['id']}/", {"title": "No longer editable"}, format="json")
        self.assertEqual(edit_approved.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_users_see_approved_reviews_only(self):
        review = self.submit_review().data
        self.client.force_authenticate(user=None)
        public_pending = self.client.get("/api/reviews/")
        self.assertEqual(public_pending.status_code, status.HTTP_200_OK)
        self.assertEqual(public_pending.data, [])
        self.client.force_authenticate(user=self.admin)
        self.client.post(f"/api/reviews/{review['id']}/moderate/", {"status": "APPROVED"}, format="json")
        self.client.force_authenticate(user=None)
        public_approved = self.client.get("/api/reviews/")
        self.assertEqual(public_approved.status_code, status.HTTP_200_OK)
        self.assertEqual(len(public_approved.data), 1)
