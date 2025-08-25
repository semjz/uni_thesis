from rest_framework import serializers
from uni_thesis.models import TimeSlot
from django.db import IntegrityError, transaction
from rest_framework import serializers
from uni_thesis.models import ThesisDefenceRequest

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
