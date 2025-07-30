from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from uni_thesis.utils import generate_unique_uni_id, generate_email
from rest_framework.validators import UniqueTogetherValidator

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

    def validate_password(self, password):
        validate_password(password)
        return password

class UserCreateSerializer(serializers.ModelSerializer, UserValidationMixin):
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "uni_id",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone_number",
            "national_code",
            "birth_date"
        ]
        extra_kwargs = {
            "password": {"write_only": True}
        }
        read_only_fields = ["uni_id", "email"]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords must match."})
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data["uni_id"] = generate_unique_uni_id(10)
        validated_data["email"] = generate_email(validated_data)
        return User.objects.create_user(**validated_data)

class UserUpdateSerializer(serializers.ModelSerializer, UserValidationMixin):

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "national_code",
            "birth_date"
        ]

    def get_validators(self):
        """
        Remove only the UniqueTogetherValidator on partial (PATCH) operations,
        but leave all other model-level validators intact.
        """
        validators = super().get_validators()
        if getattr(self, 'partial', True):
            validators = [
                v for v in validators
                if not isinstance(v, UniqueTogetherValidator)
            ]
        return validators


    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
