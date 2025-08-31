# tests/test_create_request_best_pair_model_real.py

from datetime import timedelta, time as _time
from django.utils.timezone import now
from django.urls import reverse_lazy
from rest_framework.test import APITestCase
from rest_framework import status

from uni_thesis.models import TimeSlot, ThesisDefenceRequest, DefenceSession
from uni_thesis.factories import StudentFactory, ProfessorFactory

from django.test import tag

@tag('integration')
class CreateRequestBestPairModelRealAPITestCase(APITestCase):
    """
    End-to-end test of the real model path (no mocks):
      - Create 1 student in field F
      - Create 10 professors in field F
      - Best pair (p0, p1) has 6 common future slots (09..14)  -> should win
      - Next pair (p2, p3) has only 2 common slots (09..10)
      - Others have single, non-overlapping slots
    Training data is derived from available future slots + (currently) zero theses counts,
    so only the best pair meets 'common_count >= 3' → positive label. The model trains
    on these tensors and is then used to score all candidate pairs.
    """

    def setUp(self):
        # Deterministic training (optional but helps stability)
        try:
            import torch
            torch.manual_seed(0)
        except Exception:
            pass

        # Student & field
        self.student = StudentFactory.create()
        self.field = self.student.field_of_study

        # Ten professors in the same field
        self.profs = [ProfessorFactory.create(field_of_study=self.field) for _ in range(10)]
        self.best_p1 = self.profs[0]
        self.best_p2 = self.profs[1]
        self.next_p1 = self.profs[2]
        self.next_p2 = self.profs[3]

        # Future date
        self.date = now().date() + timedelta(days=1)

        def add_slot(prof, hour):
            start = _time(hour, 0)
            end = _time(hour + 1, 0)
            TimeSlot.objects.create(
                professor=prof,
                date=self.date,
                start_time=start,
                end_time=end,
                available=True,
            )

        # Best pair: 6 common hours 09..14
        for h in [9, 10, 11, 12, 13, 14]:
            add_slot(self.best_p1, h)
            add_slot(self.best_p2, h)

        # Next-best pair: 2 common hours 09..10
        for h in [9, 10]:
            add_slot(self.next_p1, h)
            add_slot(self.next_p2, h)

        # Remaining profs: unique, non-overlapping single hours (16..21)
        hour = 16
        for p in self.profs[4:]:
            add_slot(p, hour)
            hour += 1

        # URL + payload
        self.url = reverse_lazy("uni_thesis:thesis-defence-create", kwargs={"student_id": self.student.pk})
        self.payload = {
            "thesis_title": "Graph Laplacians in Large Networks",
            "thesis_abstract": "We investigate spectral methods for community detection.",
            "field": self.field,
        }

    def test_post_uses_real_model_and_picks_best_pair(self):
        # Authenticate as the student (IsAuthenticated, IsStudentUserOrAdmin)
        self.client.force_authenticate(self.student.user)

        # POST to the real view; secure=True avoids HTTPS redirect if enabled
        resp = self.client.post(self.url, self.payload, format="json", secure=True)

        # 1) Must succeed and return the created objects + suggestion
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertIn("request", resp.data)
        self.assertIn("defence_session", resp.data)
        self.assertIn("suggestion", resp.data)
        self.assertEqual(resp.data["suggestion"].get("status"), "success")

        # 2) Load from DB
        req_id = resp.data["request"]["id"]
        req = ThesisDefenceRequest.objects.get(pk=req_id)
        session = DefenceSession.objects.get(request=req)

        # 3) Best pair chosen (order-agnostic)
        picked = {session.evaluator_id, session.observer_id}
        expected = {self.best_p1.pk, self.best_p2.pk}
        self.assertEqual(
            picked, expected,
            f"Expected best pair {expected} to be chosen by the real model, got {picked}"
        )

        # 4) Earliest shared slot (09:00–10:00) booked for the best pair
        self.assertEqual(str(session.date), str(self.date))
        self.assertEqual(session.start_time.strftime("%H:%M"), "09:00")
        self.assertEqual(session.end_time.strftime("%H:%M"), "10:00")

        # 5) Those two 09:00 slots are now booked (available=False)
        a_slot = TimeSlot.objects.get(professor=self.best_p1, date=self.date, start_time=_time(9, 0))
        b_slot = TimeSlot.objects.get(professor=self.best_p2, date=self.date, start_time=_time(9, 0))
        self.assertFalse(a_slot.available)
        self.assertFalse(b_slot.available)
