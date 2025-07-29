from rest_framework import serializers
from uni_thesis.models import Student
from .user import UserCreateSerializer, UserUpdateSerializer


class StudentCreateSerializer(serializers.ModelSerializer):
    user = UserCreateSerializer()

    class Meta:
        model = Student
        fields = [
            "user",
            "field_of_study",
            "level_of_study",
            "specialization",
        ]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_data["role"] = "Student"
        user = UserCreateSerializer().create(user_data)
        return Student.objects.create(user=user, **validated_data)

class StudentUpdateSerializer(serializers.ModelSerializer):
    # Flattened user fields, all optional
    user = UserUpdateSerializer(partial=True, required=False)

    class Meta:
        model = Student
        fields = [
            "user",
            "field_of_study",
            "level_of_study",
            "specialization",
        ]
        extra_kwargs = {
            "field_of_study": {"required": False},
            "level_of_study": {"required": False},
            "specialization": {"required": False},
            "user": {"required": False},
        }

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user = UserUpdateSerializer(
                instance=instance.user,
                data=user_data,
                partial=True,
                context=self.context
            )
            user.is_valid(raise_exception=True)
            user.save()

        return super().update(instance, validated_data)