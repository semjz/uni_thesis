# tests/test_defence_sessions_get.py

from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from uni_thesis.models import DefenceSession
from uni_thesis.factories import (
    StudentFactory,
    ProfessorFactory,
    ThesisDefenceRequestFactory,
    DefenceSessionFactory,   # ensure this exists as we discussed
)

User = get_user_model()


class DefenceSessionListAPITestCase(APITestCase):
    def setUp(self):
        # Users/roles
        self.student1 = StudentFactory.create()
        self.student2 = StudentFactory.create()
        self.prof_a = ProfessorFactory.create(field_of_study=self.student1.field_of_study)
        self.prof_b = ProfessorFactory.create(field_of_study=self.student1.field_of_study)
        self.prof_c = ProfessorFactory.create(field_of_study=self.student2.field_of_study)

        # Requests for students
        self.req1 = ThesisDefenceRequestFactory.create(student=self.student1, field=self.student1.field_of_study)
        self.req2 = ThesisDefenceRequestFactory.create(student=self.student2, field=self.student2.field_of_study)

        # Sessions:
        # s1: student1’s session, prof_a evaluator, prof_b observer
        self.s1 = DefenceSessionFactory.create(request=self.req1, evaluator=self.prof_a, observer=self.prof_b)
        # s2: student2’s session, prof_c evaluator, prof_a observer  (so prof_a is involved as observer)
        self.s2 = DefenceSessionFactory.create(request=self.req2, evaluator=self.prof_c, observer=self.prof_a)
        # s3: another session unrelated to prof_a or student1
        self.s3 = DefenceSessionFactory.create()

        self.list_url = reverse_lazy("uni_thesis:defence-session-list")

    def test_admin_sees_all_sessions(self):
        admin = User.objects.create_user(
            uni_id="9000000000", password="secret", email="admin@u.edu",
            first_name="Admin", last_name="User", is_staff=True
        )
        self.client.force_authenticate(admin)
        resp = self.client.get(self.list_url, secure=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in resp.data}
        self.assertEqual(ids, {self.s1.pk, self.s2.pk, self.s3.pk})

    def test_professor_sees_their_own_sessions(self):
        # prof_a is evaluator in s1 and observer in s2 → should see {s1, s2}
        self.client.force_authenticate(self.prof_a.user)
        resp = self.client.get(self.list_url, secure=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in resp.data}
        self.assertEqual(ids, {self.s1.pk, self.s2.pk})

    def test_student_sees_only_their_own_session(self):
        # student1 should only see s1
        self.client.force_authenticate(self.student1.user)
        resp = self.client.get(self.list_url, secure=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in resp.data]
        self.assertEqual(ids, [self.s1.pk])

    def test_user_with_no_role_sees_empty_list(self):
        # plain user not linked to Student/Professor
        user = User.objects.create_user(
            uni_id="9100000000", password="secret", email="plain@u.edu",
            first_name="Plain", last_name="User"
        )
        self.client.force_authenticate(user)
        resp = self.client.get(self.list_url, secure=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])


class DefenceSessionDetailAdminAPITestCase(APITestCase):
    def setUp(self):
        self.student = StudentFactory.create()
        self.prof1 = ProfessorFactory.create(field_of_study=self.student.field_of_study)
        self.prof2 = ProfessorFactory.create(field_of_study=self.student.field_of_study)
        self.req = ThesisDefenceRequestFactory.create(student=self.student, field=self.student.field_of_study)
        self.session = DefenceSessionFactory.create(request=self.req, evaluator=self.prof1, observer=self.prof2)

        self.detail_url = reverse_lazy("uni_thesis:defence-session-detail", kwargs={"pk": self.session.pk})

        self.admin = User.objects.create_user(
            uni_id="9900000000", password="secret", email="admin@u.edu",
            first_name="Admin", last_name="User", is_staff=True
        )

    def test_admin_can_view_any_session_detail(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.detail_url, secure=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], self.session.pk)
        self.assertEqual(resp.data["evaluator"], self.prof1.id)
        self.assertEqual(resp.data["observer"], self.prof2.id)

    def test_professor_cannot_view_detail_403(self):
        self.client.force_authenticate(self.prof1.user)
        resp = self.client.get(self.detail_url, secure=True)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_view_detail_403(self):
        self.client.force_authenticate(self.student.user)
        resp = self.client.get(self.detail_url, secure=True)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
