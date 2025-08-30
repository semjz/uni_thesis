# tests/test_create_thesis_defence_request_autobook.py

from datetime import timedelta, time as _time
from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from uni_thesis.models import ThesisDefenceRequest, DefenceSession, TimeSlot
from uni_thesis.factories import (
    StudentFactory,
    ProfessorFactory,
    ThesisDefenceRequestFactory,  # used in duplicate test
)

User = get_user_model()


def _slot_key(d, start_t, end_t) -> str:
    """Builds the exact slot key the AI/view expect: YYYY-MM-DD|HH:MM-HH:MM"""
    return f"{d.isoformat()}|{start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}"


class CreateThesisDefenceRequestAPITestCase(APITestCase):
    """
    Tests the POST view that:
      1) creates ThesisDefenceRequest
      2) immediately uses AI suggestion
      3) books a DefenceSession via serializer (atomic) — or 409s if it cannot
    """

    def setUp(self):
        self.student = StudentFactory.create()
        # Change the URL name if yours differs in urls.py
        self.url = reverse_lazy(
            "uni_thesis:thesis-defence-create",
            kwargs={"student_id": self.student.pk},
        )

        self.valid_payload = {
            "thesis_title": "Legit title",
            "thesis_abstract": "Solid abstract text for the thesis.",
            "field": self.student.field_of_study,  # keep it consistent with the student
        }
        self.invalid_payload = {
            "thesis_title": "",  # invalid per serializer rules
            # thesis_abstract omitted on purpose
        }

        # Two professors (same field as student) the AI will "choose"
        self.prof_a = ProfessorFactory(field_of_study=self.student.field_of_study)
        self.prof_b = ProfessorFactory(field_of_study=self.student.field_of_study)

        # A future 1-hour slot both can share (happy path)
        self.date = now().date() + timedelta(days=1)
        self.start = _time(9, 0)
        self.end = _time(10, 0)

    # ---- Happy path: request + session created (201) ----
    # Adjust the patch target to where your view imports this function.
    # If your view module path is different, change "uni_thesis.views..." accordingly.
    @patch("uni_thesis.views.thesis_defence.suggest_committee_for_request")
    def test_create_request_and_session_success(self, mock_suggest):
        # Seed matching available slots for BOTH professors
        TimeSlot.objects.create(
            professor=self.prof_a,
            date=self.date, start_time=self.start, end_time=self.end,
            available=True,
        )
        TimeSlot.objects.create(
            professor=self.prof_b,
            date=self.date, start_time=self.start, end_time=self.end,
            available=True,
        )

        # Mock AI suggestion to pick (prof_a, prof_b) at the exact slot
        mock_suggest.return_value = {
            "status": "success",
            "data": {
                "evaluator_id": self.prof_a.id,
                "observer_id": self.prof_b.id,
                "score": 0.92,
                "suggested_time": _slot_key(self.date, self.start, self.end),
            },
        }

        self.client.force_authenticate(self.student.user)
        resp = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("request", resp.data)
        self.assertIn("defence_session", resp.data)
        self.assertIn("suggestion", resp.data)

        # Verify DB objects
        req_id = resp.data["request"]["id"]
        req_obj = ThesisDefenceRequest.objects.get(pk=req_id)
        sess_obj = DefenceSession.objects.get(request=req_obj)
        self.assertEqual(sess_obj.evaluator_id, self.prof_a.id)
        self.assertEqual(sess_obj.observer_id, self.prof_b.id)
        self.assertEqual(str(sess_obj.date), str(self.date))
        self.assertEqual(str(sess_obj.start_time), self.start.strftime("%H:%M:%S"))
        self.assertEqual(str(sess_obj.end_time), self.end.strftime("%H:%M:%S"))

        # Slots should be booked
        a_slot = TimeSlot.objects.get(professor=self.prof_a, date=self.date, start_time=self.start)
        b_slot = TimeSlot.objects.get(professor=self.prof_b, date=self.date, start_time=self.start)
        self.assertFalse(a_slot.available)
        self.assertFalse(b_slot.available)

    # ---- AI cannot find overlap/pair → 409 and nothing created ----
    @patch("uni_thesis.views.thesis_defence.suggest_committee_for_request")
    def test_ai_no_overlap_conflict(self, mock_suggest):
        mock_suggest.return_value = {"status": "no_overlap", "message": "No pairs with common availability."}

        self.client.force_authenticate(self.student.user)
        resp = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(ThesisDefenceRequest.objects.filter(student=self.student).exists())

    # ---- Booking fails (slot missing for one prof) → 409 and nothing created ----
    @patch("uni_thesis.views.thesis_defence.suggest_committee_for_request")
    def test_booking_fails_conflict(self, mock_suggest):
        # Only prof_a has the slot; prof_b does not
        TimeSlot.objects.create(
            professor=self.prof_a,
            date=self.date, start_time=self.start, end_time=self.end,
            available=True,
        )

        mock_suggest.return_value = {
            "status": "success",
            "data": {
                "evaluator_id": self.prof_a.id,
                "observer_id": self.prof_b.id,
                "score": 0.80,
                "suggested_time": _slot_key(self.date, self.start, self.end),
            },
        }

        self.client.force_authenticate(self.student.user)
        resp = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(ThesisDefenceRequest.objects.filter(student=self.student).exists())
        self.assertIn("error", resp.data)

    # ---- Invalid payload (serializer-level 400) ----
    def test_create_request_invalid_payload(self):
        self.client.force_authenticate(self.student.user)
        resp = self.client.post(self.url, self.invalid_payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("thesis_title" in resp.data or "thesis_abstract" in resp.data)

    # ---- Student not found (404) ----
    def test_create_request_student_not_found(self):
        self.client.force_authenticate(self.student.user)
        bad_url = reverse_lazy("uni_thesis:thesis-defence-create", kwargs={"student_id": 999999})
        resp = self.client.post(bad_url, self.valid_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.data, {"error": "Student not found"})

    # ---- Duplicate forbidden (400) ----
    def test_create_request_duplicate_forbidden(self):
        # Ensure existing request (set field to satisfy model requirement)
        ThesisDefenceRequestFactory.create(student=self.student, field=self.student.field_of_study)

        self.client.force_authenticate(self.student.user)
        resp = self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.data)
        self.assertEqual(resp.data["error"], "This student already submitted a request.")


class StudentThesisDefenceRequestAPITestCase(APITestCase):
    """
    Tests the GET view that returns a student's own thesis defence request,
    restricted so non-staff students can't view others' requests.
    """

    def setUp(self):
        self.student = StudentFactory.create()
        self.other_student = StudentFactory.create()

        self.my_request = ThesisDefenceRequestFactory.create(
            student=self.student, field=self.student.field_of_study
        )
        self.other_request = ThesisDefenceRequestFactory.create(
            student=self.other_student, field=self.other_student.field_of_study
        )

        # Change the URL name if yours differs in urls.py
        self.url_my = reverse_lazy(
            "uni_thesis:student-thesis-defence-request",
            kwargs={"student_id": self.student.id},
        )
        self.url_other = reverse_lazy(
            "uni_thesis:student-thesis-defence-request",
            kwargs={"student_id": self.other_student.id},
        )

    def test_student_gets_own_request(self):
        self.client.force_authenticate(self.student.user)
        resp = self.client.get(self.url_my)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["student"], self.student.id)
        self.assertEqual(resp.data["id"], self.my_request.id)

    def test_student_cannot_get_others_request(self):
        self.client.force_authenticate(self.student.user)
        resp = self.client.get(self.url_other)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_get_any_students_request(self):
        admin = User.objects.create_user(
            uni_id="0000000000",
            password="secret123",
            email="admin@university.edu",
            first_name="Admin",
            last_name="User",
            is_staff=True,
        )
        self.client.force_authenticate(admin)
        resp = self.client.get(self.url_other)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], self.other_request.id)

    def test_404_if_request_missing_for_student(self):
        s = StudentFactory.create()
        url = reverse_lazy(
            "uni_thesis:student-thesis-defence-request",
            kwargs={"student_id": s.id},
        )
        self.client.force_authenticate(s.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
