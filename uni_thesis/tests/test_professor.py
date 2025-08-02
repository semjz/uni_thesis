from rest_framework import status
from rest_framework.test import APITestCase
from uni_thesis.factories import ProfessorFactory, StudentFactory
from django.urls import reverse_lazy

class ProfessorAPITestCase(APITestCase):

    def setUp(self):
        self.base_professor = ProfessorFactory.build()
        self.professor_user_data = {
                  "user": {
                    "password": self.base_professor.user.password,
                    "confirm_password": self.base_professor.user.password,
                    "first_name": self.base_professor.user.first_name,
                    "last_name": self.base_professor.user.last_name,
                    "phone_number": self.base_professor.user.phone_number,
                    "national_code": self.base_professor.user.national_code,
                    "birth_date": self.base_professor.user.birth_date,
                  },
                  "field_of_study": self.base_professor.field_of_study,
                  "specialization": self.base_professor.specialization,
                }
        self.professor_user_update_data = {
            "user": {"national_code":"0001111222"},
            "field_of_study": "Updated",
        }
        self.professor = ProfessorFactory.create()

    def test_create_professor_forbidden(self):
        self.url = reverse_lazy("uni_thesis:professor-list")
        self.client.force_authenticate(self.professor.user)
        response = self.client.post(self.url, self.professor_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_professor_successful(self):
        self.url = reverse_lazy("uni_thesis:professor-detail", kwargs={"pk": self.professor.pk})
        self.client.force_authenticate(self.professor.user)
        response = self.client.patch(self.url, self.professor_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_professor_forbidden(self):
        another_professor = ProfessorFactory.create()
        self.url = reverse_lazy("uni_thesis:professor-detail", kwargs={"pk": another_professor.pk})
        self.client.force_authenticate(self.professor.user)
        response = self.client.patch(self.url, self.professor_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_professor_forbidden(self):
        self.url = reverse_lazy("uni_thesis:professor-detail", kwargs={"pk": self.professor.pk})
        self.client.force_authenticate(self.professor.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_professor_successful(self):
        self.url = reverse_lazy("uni_thesis:professor-detail", kwargs={"pk": self.professor.pk})
        self.client.force_authenticate(self.professor.user)
        response = self.client.get(self.url, self.professor_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_another_professor_forbidden(self):
        another_professor = ProfessorFactory.create()
        self.url = reverse_lazy("uni_thesis:professor-detail", kwargs={"pk": another_professor.pk})
        self.client.force_authenticate(self.professor.user)
        response = self.client.get(self.url, self.professor_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_student_successful(self):
        self.url = reverse_lazy("uni_thesis:student-list")
        self.client.force_authenticate(self.professor.user)
        response = self.client.get(self.url, self.professor_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_student_successful(self):
        student = StudentFactory.create()
        self.url = reverse_lazy("uni_thesis:student-detail", kwargs={"pk": student.pk})
        self.client.force_authenticate(self.professor.user)
        response = self.client.get(self.url, self.professor_user_update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
