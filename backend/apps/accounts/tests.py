from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import CustomerProfile, User


class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.registration_data = {
            "email": "guest@example.com",
            "password": "safe-local-password",
            "first_name": "Local",
            "last_name": "Guest",
        }

    def register(self):
        return self.client.post("/api/auth/register/", self.registration_data, format="json")

    def login(self, password=None):
        return self.client.post(
            "/api/auth/login/",
            {"email": self.registration_data["email"], "password": password or self.registration_data["password"]},
            format="json",
        )

    def test_successful_registration_hashes_password_and_returns_tokens(self):
        response = self.register()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        user = User.objects.get(email=self.registration_data["email"])
        self.assertTrue(user.check_password(self.registration_data["password"]))
        self.assertEqual(response.data["user"]["role"], User.Role.CUSTOMER)

    def test_successful_login_returns_tokens_and_role(self):
        self.register()

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], User.Role.CUSTOMER)

    def test_invalid_password_is_rejected(self):
        self.register()

        response = self.login(password="wrong-password")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh_returns_access_token(self):
        registration = self.register()

        response = self.client.post(
            "/api/auth/token/refresh/",
            {"refresh": registration.data["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_authenticated_current_user_returns_user_and_role(self):
        login_response = self.register()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.registration_data["email"])
        self.assertEqual(response.data["role"], User.Role.CUSTOMER)

    def test_unauthenticated_current_user_is_rejected(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RolePermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def user_for_role(self, role):
        return User.objects.create_user(
            email=f"{role.lower()}@example.com",
            password="safe-local-password",
            role=role,
        )

    def test_all_staff_roles_can_access_staff_scope(self):
        for role in (
            User.Role.ADMIN,
            User.Role.MANAGER,
            User.Role.RECEPTIONIST,
            User.Role.HOUSEKEEPING,
        ):
            with self.subTest(role=role):
                self.client.force_authenticate(user=self.user_for_role(role))
                response = self.client.get("/api/auth/staff-scope/")
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_cannot_access_staff_scope(self):
        self.client.force_authenticate(user=self.user_for_role(User.Role.CUSTOMER))

        response = self.client.get("/api/auth/staff-scope/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_admin_can_access_admin_scope(self):
        for role, expected_status in (
            (User.Role.ADMIN, status.HTTP_200_OK),
            (User.Role.MANAGER, status.HTTP_403_FORBIDDEN),
            (User.Role.RECEPTIONIST, status.HTTP_403_FORBIDDEN),
            (User.Role.HOUSEKEEPING, status.HTTP_403_FORBIDDEN),
            (User.Role.CUSTOMER, status.HTTP_403_FORBIDDEN),
        ):
            with self.subTest(role=role):
                self.client.force_authenticate(user=self.user_for_role(role))
                response = self.client.get("/api/auth/admin-scope/")
                self.assertEqual(response.status_code, expected_status)

    def test_unauthenticated_staff_and_admin_scopes_are_rejected(self):
        self.assertEqual(
            self.client.get("/api/auth/staff-scope/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.get("/api/auth/admin-scope/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class CustomerProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            "profile-customer@example.com",
            "password",
            role=User.Role.CUSTOMER,
        )
        self.other_customer = User.objects.create_user(
            "other-customer@example.com",
            "password",
            role=User.Role.CUSTOMER,
        )
        self.profile = CustomerProfile.objects.create(user=self.customer)
        CustomerProfile.objects.create(user=self.other_customer)
        self.manager = User.objects.create_user("profile-manager@example.com", "password", role=User.Role.MANAGER)
        self.receptionist = User.objects.create_user("profile-reception@example.com", "password", role=User.Role.RECEPTIONIST)
        self.admin = User.objects.create_user("profile-admin@example.com", "password", role=User.Role.ADMIN)
        self.housekeeper = User.objects.create_user("profile-housekeeper@example.com", "password", role=User.Role.HOUSEKEEPING)

    def test_customer_registration_creates_empty_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "new-customer@example.com", "password": "safe-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(email="new-customer@example.com")
        self.assertTrue(CustomerProfile.objects.filter(user=created_user).exists())

    def test_customer_can_view_and_edit_only_own_profile(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get("/api/auth/profile/")
        update_response = self.client.patch(
            "/api/auth/profile/",
            {"phone_number": "+91 98765 43210", "city": "Bengaluru"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_email"], self.customer.email)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.city, "Bengaluru")

    def test_customer_profile_fields_are_validated(self):
        self.client.force_authenticate(user=self.customer)

        response = self.client.patch(
            "/api/auth/profile/",
            {"phone_number": "not-a-phone"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operations_staff_can_view_profiles_but_housekeeping_cannot(self):
        for user in (self.admin, self.manager, self.receptionist):
            with self.subTest(role=user.role):
                self.client.force_authenticate(user=user)
                response = self.client.get("/api/auth/profiles/")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 2)

        self.client.force_authenticate(user=self.housekeeper)
        response = self.client.get("/api/auth/profiles/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_profiles_are_not_public(self):
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get("/api/auth/profiles/").status_code, status.HTTP_401_UNAUTHORIZED)
