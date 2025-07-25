from django.conf import settings
from django.db import models

class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    field_of_study = models.CharField(max_length=100)
    level_of_study = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)

class Professor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    field_of_study = models.CharField(max_length=100)
    specialization =models.CharField(max_length=100)