from django.conf import settings
from django.db import models


class FieldOfStudy(models.TextChoices):
    COMPUTER_SCIENCE = "computer_science", "Computer Science"
    MATHEMATICS      = "mathematics", "Mathematics"
    PHYSICS          = "physics", "Physics"
    CHEMISTRY        = "chemistry", "Chemistry"
    BIOLOGY          = "biology", "Biology"
    ENGINEERING      = "engineering", "Engineering"
    MEDICINE         = "medicine", "Medicine"
    LAW              = "law", "Law"
    BUSINESS         = "business", "Business"
    ARTS_HUMANITIES  = "arts_humanities", "Arts & Humanities"

class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    field_of_study = models.CharField(
        max_length=32,
        choices=FieldOfStudy.choices,
    )
    level_of_study = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)

class Professor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    field_of_study = models.CharField(
        max_length=32,
        choices=FieldOfStudy.choices,
    )
    specialization =models.CharField(max_length=100)