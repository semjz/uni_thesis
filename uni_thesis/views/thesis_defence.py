from django.db.models import Q
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from uni_thesis.models import Student, Professor, TimeSlot, ThesisDefenceRequest, DefenceSession
from uni_thesis.permissions import IsProfessorUserOrAdmin, IsTimeslotOwnerOrAdmin, IsStudentUserOrAdmin, IsAdmin
from uni_thesis.serializers import TimeSlotInSerializer, TimeSlotSerializer, ThesisDefenceRequestSerializer, \
    DefenceSessionCreateSerializer, DefenceSessionSerializer
from AI.candidates import suggest_committee_for_request
from django.utils.dateparse import parse_date, parse_time


def me_prof(user) -> Professor:
    return get_object_or_404(Professor, user_id=user.id)


def overlaps_for_prof(professor_id, date, start_time, end_time, exclude_pk=None):
    qs = TimeSlot.objects.filter(
        professor_id=professor_id,
        date=date,
        start_time__lt=end_time,  # existing.start < new.end
        end_time__gt=start_time,  # existing.end   > new.start
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()

@extend_schema(tags=["time-slot"])
class MyTimeSlotListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/timeslots/   -> list *my* slots (scoped queryset => privacy-friendly 404s elsewhere)
    POST /api/timeslots/   -> create one or more slots for me (no overlaps for me)
    """
    permission_classes = [IsAuthenticated, IsProfessorUserOrAdmin]
    serializer_class = TimeSlotSerializer

    def get_queryset(self):
        # Scope results to the current professor (non-owners can't see → auto 404).
        prof = me_prof(self.request.user)
        return (
            TimeSlot.objects
            .filter(professor=prof)
            .order_by("date", "start_time")
        )

    def create(self, request, *args, **kwargs):
        prof = me_prof(request.user)
        payload = request.data
        items = payload if isinstance(payload, list) else [payload]

        created = []
        with transaction.atomic():
            # Serialize concurrent creations for *this* professor
            Professor.objects.select_for_update().get(pk=prof.pk)

            for item in items:
                s = TimeSlotInSerializer(data=item)
                s.is_valid(raise_exception=True)

                # Be explicit (don’t rely on dict ordering)
                date = s.validated_data["date"]
                start_time = s.validated_data["start_time"]
                end_time = s.validated_data["end_time"]

                # Per-professor overlap check
                if overlaps_for_prof(prof.pk, date, start_time, end_time):
                    return Response(
                        {"detail": "Overlaps one of your existing slots."},
                        status=status.HTTP_409_CONFLICT,  # 409 = conflict with current state
                    )

                slot = TimeSlot.objects.create(
                    professor=prof,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    available=True,
                )
                created.append(slot)

        return Response(TimeSlotSerializer(created, many=True).data, status=status.HTTP_201_CREATED)

@extend_schema(tags=["time-slot"])
class MyTimeSlotDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/timeslots/<int:pk>/
    With queryset scoping: trying to delete someone else’s slot yields a 404.
    """
    permission_classes = [IsAuthenticated, IsProfessorUserOrAdmin, IsTimeslotOwnerOrAdmin]
    serializer_class = TimeSlotSerializer  # optional, but nice for uniformity

    def get_queryset(self):
        prof = me_prof(self.request.user)
        return TimeSlot.objects.filter(professor=prof)


class CreateThesisDefenceRequestView(APIView):
    permission_classes = [IsAuthenticated]  # keep your custom perm too

    def post(self, request, student_id: int):
        # 0) student + single request check (outside tx)
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        if ThesisDefenceRequest.objects.filter(student=student).exists():
            return Response({"error": "This student already submitted a request."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 1) validate payload (outside tx)
        req_ser = ThesisDefenceRequestSerializer(data=request.data, context={"student": student})
        if not req_ser.is_valid():
            return Response(req_ser.errors, status=status.HTTP_400_BAD_REQUEST)

        supervisor_id = request.data.get("supervisor_id")

        # 2) atomic: save request → ask AI → book session
        with transaction.atomic():
            req = req_ser.save()  # we want this rolled back if anything later fails

            suggestion = suggest_committee_for_request(req, supervisor_id=supervisor_id)
            if suggestion.get("status") not in {"success", "model_unavailable"}:
                transaction.set_rollback(True)
                return Response(
                    {"error": "Automatic scheduling failed.",
                     "reason": suggestion.get("message", suggestion.get("status"))},
                    status=status.HTTP_409_CONFLICT,
                )

            data = suggestion.get("data") or {}
            slot_key = data.get("suggested_time")
            d, t1, t2 = _parse_slot_key(slot_key) if slot_key else (None, None, None)
            if not (data.get("evaluator_id") and data.get("observer_id") and d and t1 and t2):
                transaction.set_rollback(True)
                return Response(
                    {"error": "Automatic scheduling failed (no concrete slot).",
                     "suggestion": suggestion},
                    status=status.HTTP_409_CONFLICT,
                )

            ds_in = {
                "request": req.pk,
                "evaluator": data["evaluator_id"],
                "observer": data["observer_id"],
                "date": d,
                "start_time": t1,
                "end_time": t2,
                "location": "Seminar Room A",
            }
            ds_ser = DefenceSessionCreateSerializer(data=ds_in)
            if not ds_ser.is_valid():
                transaction.set_rollback(True)
                return Response(
                    {"error": "Automatic scheduling failed.", "booking_errors": ds_ser.errors},
                    status=status.HTTP_409_CONFLICT,
                )

            try:
                session = ds_ser.save()
            except (serializers.ValidationError, IntegrityError) as e:
                # Anything that blows up during create() → treat as conflict
                transaction.set_rollback(True)
                detail = getattr(e, "detail", str(e))
                return Response(
                    {"error": "Automatic scheduling failed.", "booking_errors": detail},
                    status=status.HTTP_409_CONFLICT,
                )

        # success (commit happened)
        return Response(
            {
                "request": ThesisDefenceRequestSerializer(req).data,
                "defence_session": DefenceSessionCreateSerializer(session).data
                    if hasattr(DefenceSessionCreateSerializer, "Meta") else  # optional
                {"id": session.pk},  # you likely have a read serializer already
                "suggestion": suggestion,
            },
            status=status.HTTP_201_CREATED,
        )

class StudentThesisDefenceRequestView(generics.RetrieveAPIView):
    """
    GET /students/<student_id>/thesis-defence-request/
    """
    serializer_class = ThesisDefenceRequestSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "student_id"
    lookup_url_kwarg = "student_id"

    def get_queryset(self):
        qs = ThesisDefenceRequest.objects.select_related("student")
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(student__user_id=user.id)


def _parse_slot_key(slot_key: str):
    try:
        d, times = slot_key.split("|", 1)
        s, e = times.split("-", 1)
        return parse_date(d), parse_time(s), parse_time(e)
    except Exception:
        return None, None, None


def _base_qs():
    return (
        DefenceSession.objects
        .select_related("request", "evaluator", "observer", "request__student", "request__student__user")
        .order_by("date", "start_time")
    )


class DefenceSessionListView(generics.ListAPIView):
    """
    GET /defence-sessions/
    - Admin: all sessions
    - Professor: sessions where they are evaluator OR observer
    - Student: session for their own request
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DefenceSessionSerializer

    def get_queryset(self):
        user = self.request.user
        qs = _base_qs()

        if user.is_staff:
            return qs

        prof = Professor.objects.filter(user_id=user.id).first()
        if prof:
            return qs.filter(Q(evaluator=prof) | Q(observer=prof))

        student = Student.objects.filter(user_id=user.id).first()
        if student:
            return qs.filter(request__student=student)

        return qs.none()


class DefenceSessionDetailAdminView(generics.RetrieveAPIView):
    """
    GET /defence-sessions/<pk>/ (ADMIN ONLY)
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = DefenceSessionSerializer
    queryset = _base_qs()
    lookup_field = "pk"