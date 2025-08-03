from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse_lazy

from uni_thesis.factories import UserFactory

class RegisterTests(TestCase):

    def setUp(self):
        self.base_user = UserFactory.build()
        self.user_data = {
        "first_name": self.base_user.first_name,
        "last_name": self.base_user.last_name,
        "national_code": self.base_user.national_code,
        "phone_number": self.base_user.phone_number,
        "email": self.base_user.email,
        "gender": self.base_user.gender,
        "birth_date": self.base_user.birth_date,
        "password": self.base_user.password,
        "confirm_password": self.base_user.password,
        "role": self.base_user.role,
    }
        self.url = reverse_lazy("uni_thesis:register")

    def test_valid_data_register_user(self):
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_password_short(self):
        self.user_data["password"] = "12345"
        self.user_data["confirm_password"] = "12345"
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_password_mismatch(self):
        self.user_data["confirm_password"] = "<PASSWORD>1"
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_invalid_national_code(self):
        self.user_data["national_code"] = "xxxxxxxxxx"
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("national_code", response.data)

    def test_invalid_phone_number(self):
        self.user_data["phone_number"] = "xxxxxxxxxxxx"
        response = self.client.post(self.url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)