# serializers/student.py
from .user import UserUpdateSerializer
from .base import BaseUserModelUpdateSerializer
from uni_thesis.models import Student

class StudentUpdateSerializer(BaseUserModelUpdateSerializer):
    user_serializer_class = UserUpdateSerializer

    class Meta:
        model = Student
        fields = ["user", "id", "field_of_study", "level_of_study", "specialization"]
        extra_kwargs = {f: {"required": False} for f in fields}