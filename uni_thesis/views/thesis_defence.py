from drf_spectacular.utils import extend_schema
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView

from uni_thesis.models import Student, ThesisDefenceRequest
from uni_thesis.permissions import IsProfessorUserOrAdmin, IsTimeslotOwnerOrAdmin, IsStudentUserOrAdmin
from uni_thesis.serializers.thesis_defence import ThesisDefenceRequestSerializer

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from uni_thesis.models import Professor
from uni_thesis.models import TimeSlot
from uni_thesis.serializers import TimeSlotInSerializer, TimeSlotSerializer


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

@extend_schema(tags=["time-slot"])
class CreateThesisDefenceRequestView(APIView):
    permission_classes = [IsAuthenticated, IsStudentUserOrAdmin]
    def post(self, request, student_id):
        # 1. check student exists
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        # 2. ensure student has only ONE request
        if ThesisDefenceRequest.objects.filter(student=student).exists():
            return Response(
                {"error": "This student already submitted a request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. validate and save
        serializer = ThesisDefenceRequestSerializer(data=request.data,  context={"student": student})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
