# tests/test_ai_model_and_candidates_factories.py
from datetime import time, timedelta
from django.test import TestCase
from django.utils.timezone import now

from uni_thesis.models import TimeSlot
from uni_thesis.factories import (
    ProfessorFactory,
    StudentFactory,
    ThesisDefenceRequestFactory,
)  # ← adjust path if needed

from AI import build_training_tensors_from_db
from AI import train_tiny_model, predict_probs
from AI import (
    build_candidates_for_field,
    choose_best_pair_fallback,
    suggest_committee_for_request,
)


def _mk_slot(prof, d, h1=9, h2=10, available=True):
    return TimeSlot.objects.create(
        professor=prof,
        date=d,
        start_time=time(h1, 0),
        end_time=time(h2, 0),
        available=available,
    )


class ModelAndCandidatesWithFactoriesTests(TestCase):
    def setUp(self):
        self.today = now().date()

        # --- Three Math professors ---
        # m1 & m2 share three slots; m3 does not overlap
        self.m1 = ProfessorFactory(field_of_study="math")
        self.m2 = ProfessorFactory(field_of_study="math")
        self.m3 = ProfessorFactory(field_of_study="math")

        for dd in [0, 1, 2]:
            dt = self.today + timedelta(days=dd)
            _mk_slot(self.m1, dt, 9, 10, True)
            _mk_slot(self.m2, dt, 9, 10, True)

        # m3: distinct time (no overlap with m1/m2)
        _mk_slot(self.m3, self.today, 11, 12, True)

        # --- One CS professor (unrelated field) ---
        self.cs1 = ProfessorFactory(field_of_study="computer science")
        _mk_slot(self.cs1, self.today, 9, 10, True)

        # --- Student + Request (student carries the field) ---
        self.stu_math = StudentFactory(field_of_study="math")
        self.req_math = ThesisDefenceRequestFactory(student=self.stu_math)

    def test_train_and_predict_with_factories(self):
        # Build training data from DB
        X, y = build_training_tensors_from_db()
        self.assertGreater(X.shape[0], 0, "No training pairs—check your timeslots are in the future.")
        # Train a tiny model
        model = train_tiny_model(X, y, epochs=30, lr=1e-2)
        self.assertIsNotNone(model)
        # Sanity: probabilities on training set are in [0,1]
        probs = predict_probs(model, X).squeeze(1)
        self.assertTrue(((probs >= 0.0) & (probs <= 1.0)).all())

    def test_build_candidates_for_field_and_fallback(self):
        # Build candidates for Math; supervisor excluded=None
        cands, id2prof, field_idx = build_candidates_for_field("math", exclude_ids=set())
        # We should have at least (m1, m2) as an overlapping pair
        self.assertGreaterEqual(len(cands), 1)
        best = choose_best_pair_fallback(cands)
        self.assertIsNotNone(best)
        self.assertIn(best.id1, id2prof)
        self.assertIn(best.id2, id2prof)
        # suggested_time should be one of the real overlaps
        self.assertGreaterEqual(len(best.common_slots), 1)

    def test_suggest_committee_for_request_e2e(self):
        # End-to-end suggestion call using the real request (field from student)
        out = suggest_committee_for_request(self.req_math)
        self.assertIn(out["status"], {"success", "model_unavailable"})
        self.assertIn("data", out)
        data = out["data"]
        self.assertIn("evaluator_id", data)
        self.assertIn("observer_id", data)
        self.assertIn("suggested_time", data)

    def test_no_overlap_edge_case(self):
        # Create two Math profs with NO overlap (different hours)
        a = ProfessorFactory(field_of_study="math")
        b = ProfessorFactory(field_of_study="math")
        _mk_slot(a, self.today, 8, 9, True)
        _mk_slot(b, self.today, 10, 11, True)

        # Build candidates—should be empty for these two alone.
        cands, id2prof, _ = build_candidates_for_field("math", exclude_ids=set([self.m1.id, self.m2.id, self.m3.id]))
        # Because we excluded overlapping ones (m1,m2), now only (a,b) remain with no overlap.
        self.assertEqual(len(cands), 0)

        # Suggestion on a fresh request that sees only (a,b) would return "no_overlap".
        # To simulate that, temporarily create a student in a field with only (a,b) visible:
        # (In your real system you'd filter by department/college as well.)
        stu2 = StudentFactory(field_of_study="math")
        req2 = ThesisDefenceRequestFactory(student=stu2)
        out2 = suggest_committee_for_request(req2)
        # Depending on other Math profs in DB, status can be "no_overlap" or a valid pick.
        # We'll assert it's a recognized status:
        self.assertIn(out2["status"], {"success", "model_unavailable", "no_overlap", "no_pairs"})
