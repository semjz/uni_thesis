# tests/test_ai_training_data_factories.py
from datetime import time, timedelta
from django.test import TestCase
from django.utils.timezone import now

from uni_thesis.models import TimeSlot
from uni_thesis.factories import ProfessorFactory  # ← adjust path if needed
from AI import fetch_professor_views, build_training_tensors_from_db


def _mk_slot(prof, d, h1=9, h2=10, available=True):
    """Quick helper to add a TimeSlot."""
    return TimeSlot.objects.create(
        professor=prof,
        date=d,
        start_time=time(h1, 0),
        end_time=time(h2, 0),
        available=available,
    )


class TrainingDataWithFactoriesTests(TestCase):
    def setUp(self):
        self.today = now().date()

        # Two Math profs with THREE overlapping future slots
        self.m1 = ProfessorFactory(field_of_study="math")
        self.m2 = ProfessorFactory(field_of_study="math")

        for dd in [0, 1, 2]:
            dt = self.today + timedelta(days=dd)
            _mk_slot(self.m1, dt, 9, 10, True)
            _mk_slot(self.m2, dt, 9, 10, True)

        # One AI prof with a different time (no overlap with Math pair)
        self.ai1 = ProfessorFactory(field_of_study="computer science")
        _mk_slot(self.ai1, self.today, 11, 12, True)

    def test_fetch_professor_views_uses_future_available_slots(self):
        views = fetch_professor_views()
        # We should see at least 3 professors
        self.assertGreaterEqual(len(views), 3)
        # Math profs must have non-empty slots
        math_views = [v for v in views if v.field == "math"]
        self.assertTrue(all(len(v.slots) >= 3 for v in math_views))

    def test_build_training_tensors_from_db_produces_pairs(self):
        X, y = build_training_tensors_from_db()
        # At least one training pair (m1, m2)
        self.assertGreater(X.shape[0], 0, "Expected at least one training pair")
        self.assertEqual(X.shape[1], 4)  # [t1, t2, common_count, field_idx]
        self.assertEqual(y.shape[1], 1)  # binary label column
