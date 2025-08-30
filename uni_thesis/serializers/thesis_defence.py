from rest_framework import serializers
from uni_thesis.models import TimeSlot
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.timezone import now
from uni_thesis.models import (
    DefenceSession,
    ProfessorAssignment,
    ThesisDefenceRequest,
    Professor,
    TimeSlot,
)

# Input for creating a timeslot (per professor)
class TimeSlotInSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError({"end_time": "end_time must be greater than start_time."})
        return attrs

class TimeSlotSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="pk")
    class Meta:
        model = TimeSlot
        fields = ["id", "date", "start_time", "end_time", "available"]



class ThesisDefenceRequestSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="pk")
    # student comes from URL; expose it read-only in the response
    student = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ThesisDefenceRequest
        fields = [
            "id",
            "student",
            "thesis_title",
            "thesis_abstract",
            "field",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["student", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        """
        Ensure we have a student in context and prevent a second request.
        (Nice UX; DB will also enforce via OneToOne under race conditions.)
        """
        student = self.context.get("student")
        if student is None:
            raise serializers.ValidationError({"student": "Student must be provided via context."})

        if ThesisDefenceRequest.objects.filter(student=student).exists():
            raise serializers.ValidationError(
                {"error": "This student already submitted a request."}
            )
        return attrs

    def create(self, validated_data):
        student = self.context["student"]
        try:
            with transaction.atomic():
                return ThesisDefenceRequest.objects.create(student=student, **validated_data)
        except IntegrityError:
            # In case of a concurrency race with the OneToOne(student)
            raise serializers.ValidationError(
                {"error": "This student already submitted a request."}
            )


class DefenceSessionSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="pk")
    request = serializers.PrimaryKeyRelatedField(read_only=True)
    evaluator = serializers.PrimaryKeyRelatedField(read_only=True)
    observer = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = DefenceSession
        fields = [
            "id",
            "request",
            "evaluator",
            "observer",
            "date",
            "start_time",
            "end_time",
            "location",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

class DefenceSessionCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a session.

    Expect payload like:
    {
      "request": 123,
      "evaluator": 10,
      "observer": 22,
      "date": "2025-09-01",
      "start_time": "09:00",
      "end_time": "10:00",
      "location": "Seminar Room A"
    }
    """
    request = serializers.PrimaryKeyRelatedField(queryset=ThesisDefenceRequest.objects.all())
    evaluator = serializers.PrimaryKeyRelatedField(queryset=Professor.objects.all())
    observer = serializers.PrimaryKeyRelatedField(queryset=Professor.objects.all())
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    location = serializers.CharField(max_length=100)

    def validate(self, attrs):
        req: ThesisDefenceRequest = attrs["request"]
        evaluator: Professor = attrs["evaluator"]
        observer: Professor = attrs["observer"]
        date = attrs["date"]
        start_time = attrs["start_time"]
        end_time = attrs["end_time"]

        # Basic time sanity
        if end_time <= start_time:
            raise serializers.ValidationError({"end_time": "end_time must be greater than start_time."})

        # Professors must differ (DB constraint also enforces it)
        if evaluator.id == observer.id:
            raise serializers.ValidationError({"observer": "Observer must be different from evaluator."})

        # One session per request (OneToOne)
        if DefenceSession.objects.filter(request=req).exists():
            raise serializers.ValidationError({"request": "This request already has a defence session."})

        # Optional: you may want only 'pending' requests to be schedulable
        if req.status not in {"pending", "accepted"}:
            raise serializers.ValidationError({"request": f"Cannot schedule a session for a {req.status} request."})

        # Optional business rule: session should be today or future
        if date < now().date():
            raise serializers.ValidationError({"date": "Session date must not be in the past."})

        # (No DB hits here beyond .exists(); timeslot checks are done in create() with row locking)
        return attrs

    def create(self, validated_data):
        """
        Creates the session, books both TimeSlots (available=False),
        and creates ProfessorAssignment rows. All in a single atomic tx.
        """
        req: ThesisDefenceRequest = validated_data["request"]
        evaluator: Professor = validated_data["evaluator"]
        observer: Professor = validated_data["observer"]
        date = validated_data["date"]
        start_time = validated_data["start_time"]
        end_time = validated_data["end_time"]
        location = validated_data["location"]

        with transaction.atomic():
            # Lock the relevant timeslot rows to avoid race conditions / double bookings
            # We require exact (date, start_time, end_time) matches and available=True.
            eval_slot_qs = (
                TimeSlot.objects
                .select_for_update()
                .filter(
                    professor=evaluator,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    available=True,
                )
            )
            obs_slot_qs = (
                TimeSlot.objects
                .select_for_update()
                .filter(
                    professor=observer,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    available=True,
                )
            )

            eval_slot = eval_slot_qs.first()
            obs_slot = obs_slot_qs.first()

            if eval_slot is None:
                raise serializers.ValidationError(
                    {"evaluator": "Evaluator does not have the specified available timeslot."}
                )
            if obs_slot is None:
                raise serializers.ValidationError(
                    {"observer": "Observer does not have the specified available timeslot."}
                )

            # Mark both slots as booked
            eval_slot.available = False
            obs_slot.available = False
            eval_slot.save(update_fields=["available"])
            obs_slot.save(update_fields=["available"])

            # Create the session (DB constraints will re-check times and distinct profs)
            session = DefenceSession.objects.create(
                request=req,
                evaluator=evaluator,
                observer=observer,
                date=date,
                start_time=start_time,
                end_time=end_time,
                location=location,
            )

            # Create assignments (optional but typically useful)
            ProfessorAssignment.objects.create(
                professor=evaluator, request=req, role="evaluator", confirmed=True
            )
            ProfessorAssignment.objects.create(
                professor=observer, request=req, role="observer", confirmed=True
            )

            # Flip request status to accepted (optional; adjust to your flow)
            if req.status != "accepted":
                req.status = "accepted"
                req.save(update_fields=["status", "updated_at"])

            return session
