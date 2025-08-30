from django.db import models
from django.db.models import Q, F

from .accounts import Professor, Student


class TimeSlot(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name="time_slots")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    available = models.BooleanField(default=True)  # True=offered, False=booked/unavailable

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(end_time__gt=F("start_time")),
                                   name="timeslot_end_after_start"),
            models.UniqueConstraint(fields=["professor", "date", "start_time"],
                                    name="uniq_prof_date_start_end"),
        ]
        indexes = [
            models.Index(fields=["professor", "date", "start_time"]),
            models.Index(fields=["professor", "available", "date", "start_time"]),
        ]

    def __str__(self):
        return f"{self.professor.id} | {self.start_at}–{self.end_at}"

class ThesisDefenceRequest(models.Model):
    STATUS_CHOICES = [
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("pending", "Pending"),
    ]
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    thesis_title = models.CharField(max_length=100)
    thesis_abstract = models.TextField()
    field = models.CharField(max_length=100)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.thesis_title}"

class ProfessorAssignment(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE)
    request = models.ForeignKey(ThesisDefenceRequest, on_delete=models.CASCADE)
    ROLE_CHOICES = [
        ("evaluator", "Evaluator"),
        ("observer", "Observer")
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    confirmed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["professor", "request"], name="unique_prof_request")
        ]

class DefenceSession(models.Model):
    request = models.OneToOneField(ThesisDefenceRequest, on_delete=models.CASCADE, primary_key=True)
    evaluator= models.ForeignKey(Professor, on_delete=models.CASCADE, related_name="evaluator_sessions")
    observer = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name="observer_sessions")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(end_time__gt=F("start_time")),
                                   name="session_end_after_start"),
            models.CheckConstraint(check=~Q(evaluator=F("observer")),
                                   name="evaluator_and_observer_must_differ"),
        ]
        indexes = [models.Index(fields=["date", "start_time"])]

    def __str__(self):
        return f"Defence for {self.request} on {self.date} at {self.location}"