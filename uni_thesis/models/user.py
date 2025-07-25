from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models
from uni_thesis.managers import CustomUserManger
from django.utils.translation import gettext_lazy as _

class User(AbstractBaseUser, PermissionsMixin):
    uni_id = models.CharField(max_length=12, validators=[MinLengthValidator(8)], unique=True)
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"),max_length=50)
    last_name = models.CharField(_("last name"),max_length=50)

    phone_number = models.CharField(_("phone number"), max_length=13, validators=[MinLengthValidator(11)]
                                    , unique=True)
    national_code = models.CharField(_("national code"), max_length=10, validators=[MinLengthValidator(10)]
                                     , unique=True)

    GENDERS_CHOICES = [("male", "male"), ("female", "female")]
    gender = models.CharField(choices=GENDERS_CHOICES, max_length=10)

    ROLES_CHOICES = [("Student", "Student"), ("Professor", "Professor"),("Admin", "Admin")]
    role = models.CharField(_("role"), choices=ROLES_CHOICES, max_length=20)

    birth_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'uni_id'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    objects = CustomUserManger()

    def __str__(self):
        return f"{self.uni_id} - {self.first_name} {self.last_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['first_name', 'last_name']
                                    , name='unique full name')
        ]

