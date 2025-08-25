from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from rest_framework import status
from rest_framework.test import APITestCase

from uni_thesis.models import TimeSlot, ThesisDefenceRequest, Professor
from uni_thesis.factories import (
    StudentFactory,
    ProfessorFactory,
    ThesisDefenceRequestFactory,
)
User = get_user_model()


# ------------------------------
# Helpers for time slot payloads
# ------------------------------
def slot_payload(date="2025-08-05", start="08:00", end="10:00"):
    return {"date": date, "start_time": start, "end_time": end}


# ============================================================
# TimeSlot: List & Create (MyTimeSlotListCreateView)
# ============================================================

class TimeSlotListCreateAPITestCase(APITestCase):
    def setUp(self):
        # Professors A & B
        self.prof_a: Professor = ProfessorFactory.create()
        self.prof_b: Professor = ProfessorFactory.create()

        # Student (to verify professor-only permission blocks students)
        self.student = StudentFactory.create()

        # URLs
        self.list_create_url = reverse_lazy("uni_thesis:timeslot-list-create")

    def test_list_returns_only_my_slots(self):
        # Given: A has 1 slot, B has 1 slot
        my_slot = TimeSlot.objects.create(
            professor=self.prof_a, date="2025-08-05", start_time="08:00", end_time="10:00", available=True
        )
        TimeSlot.objects.create(
            professor=self.prof_b, date="2025-08-06", start_time="10:00", end_time="12:00", available=True
        )

        # When: A lists their timeslots
        self.client.force_authenticate(self.prof_a.user)
        resp = self.client.get(self.list_create_url)

        # Then: Only A's slot is returned
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["id"], my_slot.id)

    def test_create_timeslot_success(self):
        self.client.force_authenticate(self.prof_a.user)
        payload = slot_payload("2025-08-07", "09:00", "11:00")

        resp = self.client.post(self.list_create_url, payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # one item created (API returns list if you post list; here single -> list with one or a single? Your view returns list of created)
        self.assertEqual(len(resp.data), 1)
        created_id = resp.data[0]["id"]
        created = TimeSlot.objects.get(pk=created_id)
        self.assertEqual(created.professor_id, self.prof_a.id)
        self.assertTrue(created.available)

    def test_create_timeslot_overlap_conflict(self):
        # Existing 08:00–10:00 for A
        TimeSlot.objects.create(
            professor=self.prof_a, date="2025-08-05", start_time="08:00", end_time="10:00", available=True
        )

        self.client.force_authenticate(self.prof_a.user)
        # Overlaps: 09:00–11:00
        resp = self.client.post(self.list_create_url, slot_payload("2025-08-05", "09:00", "11:00"), format="json")

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("detail", resp.data)

    def test_create_timeslot_bulk_success(self):
        self.client.force_authenticate(self.prof_a.user)
        payload = [
            slot_payload("2025-08-10", "08:00", "10:00"),
            slot_payload("2025-08-11", "10:00", "12:00"),
        ]
        resp = self.client.post(self.list_create_url, payload, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resp.data), 2)
        ids = [row["id"] for row in resp.data]
        self.assertEqual(TimeSlot.objects.filter(pk__in=ids, professor=self.prof_a).count(), 2)

    def test_student_forbidden_on_timeslot_endpoints(self):
        # Permission class IsProfessorUserOrAdmin should block non-professors here
        self.client.force_authenticate(self.student.user)
        resp_list = self.client.get(self.list_create_url)
        self.assertEqual(resp_list.status_code, status.HTTP_403_FORBIDDEN)

        resp_post = self.client.post(self.list_create_url, slot_payload(), format="json")
        self.assertEqual(resp_post.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# TimeSlot: Delete (MyTimeSlotDeleteView)
# ============================================================

class TimeSlotDeleteAPITestCase(APITestCase):
    def setUp(self):
        self.prof_a: Professor = ProfessorFactory.create()
        self.prof_b: Professor = ProfessorFactory.create()
        self.student = StudentFactory.create()

    def _delete_url(self, slot_id):
        return reverse_lazy("uni_thesis:timeslot-delete", kwargs={"pk": slot_id})

    def test_delete_own_slot_success(self):
        slot = TimeSlot.objects.create(
            professor=self.prof_a, date="2025-08-05", start_time="08:00", end_time="10:00", available=True
        )
        self.client.force_authenticate(self.prof_a.user)
        resp = self.client.delete(self._delete_url(slot.id))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TimeSlot.objects.filter(pk=slot.id).exists())

    def test_delete_others_slot_scoped_404(self):
        # Slot belongs to B
        slot_b = TimeSlot.objects.create(
            professor=self.prof_b, date="2025-08-06", start_time="10:00", end_time="12:00", available=True
        )

        # A tries to delete -> queryset scoping should yield 404
        self.client.force_authenticate(self.prof_a.user)
        resp = self.client.delete(self._delete_url(slot_b.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(TimeSlot.objects.filter(pk=slot_b.id).exists())

    def test_student_forbidden_delete(self):
        slot = TimeSlot.objects.create(
            professor=self.prof_a, date="2025-08-05", start_time="08:00", end_time="10:00", available=True
        )
        self.client.force_authenticate(self.student.user)
        resp = self.client.delete(self._delete_url(slot.id))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(TimeSlot.objects.filter(pk=slot.id).exists())