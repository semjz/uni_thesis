# serializers/student.py
from .user import UserCreateSerializer, UserUpdateSerializer
from .base import BaseUserModelCreateSerializer
from .base import BaseUserModelUpdateSerializer
from uni_thesis.models import Professor


class ProfessorUpdateSerializer(BaseUserModelUpdateSerializer):
    user_serializer_class = UserUpdateSerializer

    class Meta:
        model = Professor
        fields = ["user", "field_of_study",  "specialization"]
        extra_kwargs = {f: {"required": False} for f in fields}