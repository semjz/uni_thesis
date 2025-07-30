# serializers/student.py
from .user import UserCreateSerializer, UserUpdateSerializer
from .base import BaseUserModelCreateSerializer
from .base import BaseUserModelUpdateSerializer
from uni_thesis.models import Student

class StudentCreateSerializer(BaseUserModelCreateSerializer):
    user_serializer_class = UserCreateSerializer
    role = "Student"

    class Meta:
        model = Student
        fields = ["user", "field_of_study", "level_of_study", "specialization"]

class StudentUpdateSerializer(BaseUserModelUpdateSerializer):
    user_serializer_class = UserUpdateSerializer

    class Meta:
        model = Student
        fields = ["user", "field_of_study", "level_of_study", "specialization"]
        extra_kwargs = {f: {"required": False} for f in fields}