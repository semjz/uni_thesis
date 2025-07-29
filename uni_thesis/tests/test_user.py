from django.test import TestCase
from uni_thesis.serializers import UserSerializer
from uni_thesis.factories import UserFactory

class CreateUserSerializerTests(TestCase):

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

    def test_valid_data_creates_user(self):
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertTrue(user.check_password(self.user_data["password"]))

    def test_password_short(self):
        self.user_data["password"] = "12345"
        self.user_data["confirm_password"] = "12345"
        serializer = UserSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_mismatch(self):
        self.user_data["confirm_password"] = "<PASSWORD>1"
        serializer = UserSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Passwords must match!", serializer.errors["non_field_errors"])

    def test_invalid_national_code(self):
        self.user_data["national_code"] = "123456"
        serializer = UserSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("national_code", serializer.errors)

    def test_invalid_phone_number(self):
        self.user_data["phone_number"] = "123456"
        serializer = UserSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone_number", serializer.errors)