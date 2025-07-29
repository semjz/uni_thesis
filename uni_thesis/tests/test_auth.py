import jwt
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from uni_thesis.factories import UserFactory
from django.urls import reverse_lazy

User = get_user_model()

class LoginTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse_lazy('uni_thesis:login')
        cls.user_data = UserFactory.build()
        cls.user = UserFactory.create(
            uni_id=cls.user_data.uni_id,
        )
        cls.user.set_password(cls.user_data.password)
        cls.user.save()

        cls.payload = {
            "uni_id": cls.user_data.uni_id,
            "password": cls.user_data.password,
        }

    def test_login_successful(self):
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        access_token = response.data["access"]
        decoded = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])


        self.assertEqual(int(decoded["user_id"]), self.user.id)

    def test_login_unsuccessful_wrong_password(self):
        bad_payload = {
            "uni_id": self.payload["uni_id"],
            "password": "<PASSWORD>",
        }
        response = self.client.post(self.url, bad_payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_login_unsuccessful_wrong_uni_id(self):
        bad_payload = {
            "uni_id": "xxxx",
            "password": self.payload["password"],
        }
        response = self.client.post(self.url, bad_payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
