from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

from .models import Room, RoomType


class RoomsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.room_type = RoomType.objects.create(
            name="Deluxe",
            description="A comfortable room",
            base_price=Decimal("125.00"),
            capacity=2,
            amenities=["wifi", "breakfast"],
        )
        self.inactive_type = RoomType.objects.create(
            name="Closed Suite",
            base_price=Decimal("250.00"),
            capacity=4,
            active=False,
        )
        self.available_room = Room.objects.create(room_number="101", room_type=self.room_type, floor=1)
        Room.objects.create(room_number="102", room_type=self.room_type, floor=1, status=Room.Status.OCCUPIED)
        self.admin = User.objects.create_user("admin@example.com", "password", role=User.Role.ADMIN)
        self.manager = User.objects.create_user("manager@example.com", "password", role=User.Role.MANAGER)
        self.receptionist = User.objects.create_user("reception@example.com", "password", role=User.Role.RECEPTIONIST)
        self.customer = User.objects.create_user("customer@example.com", "password", role=User.Role.CUSTOMER)

    def test_public_users_see_active_types_and_available_rooms(self):
        types_response = self.client.get("/api/rooms/types/")
        rooms_response = self.client.get("/api/rooms/")

        self.assertEqual(types_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["name"] for item in types_response.data], ["Deluxe"])
        self.assertEqual(rooms_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["room_number"] for item in rooms_response.data], ["101"])

    def test_receptionist_can_view_all_rooms(self):
        self.client.force_authenticate(user=self.receptionist)

        response = self.client.get("/api/rooms/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_manager_and_admin_can_create_and_edit_rooms(self):
        for user in (self.manager, self.admin):
            with self.subTest(role=user.role):
                self.client.force_authenticate(user=user)
                response = self.client.post(
                    "/api/rooms/",
                    {"room_number": f"{user.role}-1", "room_type": self.room_type.id, "floor": 2, "status": "AVAILABLE"},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                edit_response = self.client.patch(
                    f"/api/rooms/{response.data['id']}/",
                    {"notes": "Updated by authorized staff"},
                    format="json",
                )
                self.assertEqual(edit_response.status_code, status.HTTP_200_OK)

    def test_customer_cannot_modify_rooms(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            "/api/rooms/",
            {"room_number": "999", "room_type": self.room_type.id, "floor": 9},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unique_room_numbers_and_positive_values_are_validated(self):
        self.client.force_authenticate(user=self.manager)
        duplicate_response = self.client.post(
            "/api/rooms/",
            {"room_number": "101", "room_type": self.room_type.id, "floor": 1},
            format="json",
        )
        invalid_type_response = self.client.post(
            "/api/rooms/types/",
            {"name": "Invalid", "base_price": 0, "capacity": 0},
            format="json",
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_type_response.status_code, status.HTTP_400_BAD_REQUEST)
