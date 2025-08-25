from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse_lazy

from uni_thesis.factories import StudentFactory, ThesisDefenceRequestFactory  # adjust if paths differ
from uni_thesis.models import ThesisDefenceRequest

User = get_user_model()


class CreateThesisDefenceRequestAPITestCase(APITestCase):
    def setUp(self):
        # a base student to authenticate with
        self.student = StudentFactory.create()

        # common payloads
        self.valid_payload = {
            "thesis_title": "Legit title",
            "thesis_abstract": "Solid abstract text for the thesis.",
            "field" : "Computer"
        }
        self.invalid_payload = {
            "thesis_title": "",  # missing/invalid; adjust to your serializer rules
            # "thesis_abstract" omitted on purpose
        }

    def _url(self, student_id):
        # Adjust the URL name/namespace if yours differs
        return reverse_lazy("uni_thesis:thesis-defence-create", kwargs={"student_id": student_id})

    def test_create_request_successful(self):
        self.client.force_authenticate(self.student.user)
        url = self._url(self.student.pk)

        response = self.client.post(url, self.valid_payload, format="json")

        print(response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["thesis_title"], self.valid_payload["thesis_title"])
        self.assertEqual(response.data["thesis_abstract"], self.valid_payload["thesis_abstract"])

        # ensure it's linked correctly
        created_id = response.data.get("id")
        self.assertIsNotNone(created_id)
        obj = ThesisDefenceRequest.objects.get(id=created_id)
        self.assertEqual(obj.student_id, self.student.id)

    def test_create_request_student_not_found(self):
        self.client.force_authenticate(self.student.user)
        url = self._url(student_id=999999)  # non-existent
        response = self.client.post(url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"error": "Student not found"})

    def test_create_request_duplicate_forbidden(self):
        self.client.force_authenticate(self.student.user)
        # existing request for this student
        ThesisDefenceRequestFactory.create(student=self.student)

        url = self._url(self.student.pk)
        response = self.client.post(url, self.valid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "This student already submitted a request.")

    def test_create_request_invalid_payload(self):
        self.client.force_authenticate(self.student.user)
        url = self._url(self.student.pk)

        response = self.client.post(url, self.invalid_payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Adjust field names according to your serializer's required fields
        self.assertTrue("thesis_title" in response.data or "thesis_abstract" in response.data)

class StudentThesisDefenceRequestAPITestCase(APITestCase):
    def setUp(self):
        self.student = StudentFactory.create()
        self.other_student = StudentFactory.create()

        # Each with/without a request
        self.my_request = ThesisDefenceRequestFactory.create(student=self.student)
        self.other_request = ThesisDefenceRequestFactory.create(student=self.other_student)

        self.url_my = reverse_lazy(
            "uni_thesis:student-thesis-defence-request", kwargs={"student_id": self.student.id}
        )
        self.url_other = reverse_lazy(
            "uni_thesis:student-thesis-defence-request", kwargs={"student_id": self.other_student.id}
        )

    def test_student_gets_own_request(self):
        self.client.force_authenticate(self.student.user)
        resp = self.client.get(self.url_my)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["student"], self.student.id)
        self.assertEqual(resp.data["id"], self.my_request.id)

    def test_student_cannot_get_other_students_request_404(self):
        self.client.force_authenticate(self.student.user)
        resp = self.client.get(self.url_other)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_get_any_students_request(self):
        admin = User.objects.create_user(uni_id="00000000", password="1234567",email="test@yahoo.com" ,first_name="test", last_name="test",
                                         is_staff=True, is_superuser=False)
        self.client.force_authenticate(admin)
        resp = self.client.get(self.url_other)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], self.other_request.id)

    def test_404_if_request_missing_for_student(self):
        # Create a student with no request
        s = StudentFactory.create()
        url = reverse_lazy("uni_thesis:student-thesis-defence-request", kwargs={"student_id": s.id})
        self.client.force_authenticate(s.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
