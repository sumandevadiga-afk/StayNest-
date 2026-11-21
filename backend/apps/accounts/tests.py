from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import User


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
