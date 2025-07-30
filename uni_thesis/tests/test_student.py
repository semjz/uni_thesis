from rest_framework import status
from rest_framework.test import APITestCase
from uni_thesis.factories import StudentFactory, UserFactory
from django.urls import reverse_lazy

class StudentAPITestCase(APITestCase):

    def setUp(self):
        self.base_student = StudentFactory.build()
        self.student_user_data = {
                  "user": {
                    "password": self.base_student.user.password,
                    "confirm_password": self.base_student.user.password,
                    "first_name": self.base_student.user.first_name,
                    "last_name": self.base_student.user.last_name,
                    "phone_number": self.base_student.user.phone_number,
                    "national_code": self.base_student.user.national_code,
                    "birth_date": self.base_student.user.birth_date,
                  },
                  "field_of_study": self.base_student.field_of_study,
                  "level_of_study": self.base_student.level_of_study,
                  "specialization": self.base_student.specialization,
                }
        self.student_user_update_data = {
            "user": {"national_code":"0001111222"},
            "field_of_study": "Updated",
        }
        self.student = StudentFactory.create()

    def test_create_student_forbidden(self):
        self.url = reverse_lazy("uni_thesis:student-list")
        self.client.force_authenticate(self.student.user)
        response = self.client.post(self.url, self.student_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_student_successful(self):
        self.url = reverse_lazy("uni_thesis:student-detail", kwargs={"pk": self.student.pk})
        self.client.force_authenticate(self.student.user)
        response = self.client.patch(self.url, self.student_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_student_forbidden(self):
        another_student = StudentFactory.create()
        self.url = reverse_lazy("uni_thesis:student-detail", kwargs={"pk": another_student.pk})
        self.client.force_authenticate(self.student.user)
        response = self.client.patch(self.url, self.student_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_student_forbidden(self):
        self.url = reverse_lazy("uni_thesis:student-detail", kwargs={"pk": self.student.pk})
        self.client.force_authenticate(self.student.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_student_successful(self):
        self.url = reverse_lazy("uni_thesis:student-detail", kwargs={"pk": self.student.pk})
        self.client.force_authenticate(self.student.user)
        response = self.client.get(self.url, self.student_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_another_student_forbidden(self):
        another_student = StudentFactory.create()
        self.url = reverse_lazy("uni_thesis:student-detail", kwargs={"pk": another_student.pk})
        self.client.force_authenticate(self.student.user)
        response = self.client.get(self.url, self.student_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
