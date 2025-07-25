from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from datetime import date, time
from uni_thesis.models import TimeSlot, ProfessorAssignment
from uni_thesis.factories import ProfessorFactory, ThesisDefenceRequestFactory

class TimeSlotTests(TestCase):
    def setUp(self):
        self.prof = ProfessorFactory()

    def test_valid_timeslot(self):
        slot = TimeSlot(
            professor=self.prof,
            date=date.today(),
            start_time=time(hour=10, minute=0),
            end_time=time(hour=11, minute=0),
        )

        slot.full_clean()

    def test_invalid_timeslot(self):
        slot = TimeSlot(
            professor=self.prof,
            date=date.today(),
            start_time=time(hour=12, minute=0),
            end_time=time(hour=11, minute=0),
        )

        with self.assertRaises(ValidationError):
            slot.full_clean()


    def test_duplicate_timeslot(self):
        TimeSlot.objects.create(
            professor=self.prof,
            date=date.today(),
            start_time=time(hour=10, minute=0),
            end_time=time(hour=11, minute=0),
        )
        with self.assertRaises(IntegrityError):
            TimeSlot.objects.create(
                professor=self.prof,
                date=date.today(),
                start_time=time(hour=10, minute=0),
                end_time=time(hour=12, minute=0),
            )

class ProfessorAssignmentTests(TestCase):
    def setUp(self):
        self.prof = ProfessorFactory()
        self.request = ThesisDefenceRequestFactory()

    def test_valid_assignment(self):
        assignment = ProfessorAssignment.objects.create(
            professor=self.prof,
            request=self.request,
            role="evaluator"
        )
        self.assertFalse(assignment.confirmed)
        self.assertTrue(assignment.role, "evaluator")

    def test_invalid_role(self):
        assignment = ProfessorAssignment.objects.create(
            professor=self.prof,
            request=self.request,
            role="invalid"
        )

        with self.assertRaises(ValidationError):
            assignment.full_clean()

    def test_duplicate_assignment_same_role(self):
        ProfessorAssignment.objects.create(
            professor=self.prof,
            request=self.request,
            role="observer"
        )

        with self.assertRaises(IntegrityError):
            ProfessorAssignment.objects.create(
                professor=self.prof,
                request=self.request,
                role="observer"
            )

    def test_assignment_same_professor_different_roles(self):
        ProfessorAssignment.objects.create(
            professor=self.prof,
            request=self.request,
            role="observer"
        )

        with self.assertRaises(IntegrityError):
            ProfessorAssignment.objects.create(
                professor=self.prof,
                request=self.request,
                role="evaluator"
            )
