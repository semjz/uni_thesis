from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from uni_thesis.utils import random_numeric_string

User = get_user_model()

# Shared Validation Mixin (SRP + DRY)
class UserValidationMixin:
    def validate_national_code(self, national_code):
        if not national_code.isnumeric():
            raise serializers.ValidationError("National code must only contain digits!")
        return national_code

    def validate_phone_number(self, phone_number):
        phone_number = phone_number.replace('+98', '0')
        if not phone_number.isnumeric():
            raise serializers.ValidationError("Phone number must only contain digits!")
        return phone_number

# Base Serializer for Sahred Logic
class BaseUserSerializer(UserValidationMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "user_id", "first_name", "last_name", "national_code", "phone_number",
            "email", "gender", "birth_date"
        ]
        read_only_fields = ["user_id", "email"]

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


# Full Update
class FullUpdateUserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer):
        fields = BaseUserSerializer.Meta.fields + ["role"]


class PartialUpdateUserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer):
        fields = BaseUserSerializer.Meta.fields.remove("user_id")

# user Creation
class CreateUserSerializer(BaseUserSerializer):
    confirm_password = serializers.CharField(max_length=20, required=True, write_only=True)

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + ["role", "password", "confirm_password"]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate_password(self, password):
        validate_password(password)
        return password

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords must match!")
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data["uni_id"] = generate_unique_uni_id(10)
        validated_data["email"] = generate_email(validated_data)
        return User.objects.create_user(**validated_data)

def generate_unique_uni_id(n):
    return random_numeric_string(n)

def generate_email(validated_data):
    uni_id = validated_data.get("uni_id")
    role = validated_data.get("role")


    if role == "Student":
        return f"{uni_id}.student@university.edu"

    elif role == "Professor":
        return f"{uni_id}.professor@university.edu"

    else:
        return f"{uni_id}.admin@university.edu"