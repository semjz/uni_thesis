from rest_framework import serializers

class BaseUserModelCreateSerializer(serializers.ModelSerializer):
    """
    Abstract base serializer for models that have a nested 'user' field.
    Subclasses must define:
      - user_serializer_class
      - role (string, like "Student" or "Professor")
    """
    user = None  # Placeholder

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "user_serializer_class"):
            raise NotImplementedError("You must set `user_serializer_class` in subclass")
        cls._declared_fields["user"] = cls.user_serializer_class(required=False)

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        user_data["role"] = self.role
        user = self.user_serializer_class().create(user_data)
        return self.Meta.model.objects.create(user=user, **validated_data)

class BaseUserModelUpdateSerializer(serializers.ModelSerializer):
    """
    Abstract base update serializer for models with nested user data.
    Subclasses must define:
      - user_serializer_class
    """
    user = None  # Placeholder

    def __init_subclass__(cls, **kwargs):
        if not hasattr(cls, "user_serializer_class"):
            raise NotImplementedError("You must set `user_serializer_class` in subclass")
        cls._declared_fields["user"] = cls.user_serializer_class(required=False, partial=True)

    def validate(self, attrs):
        user_data = attrs.get("user")
        if not attrs and not user_data:
            raise serializers.ValidationError("You must provide at least one field to update.")
        return attrs

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user = self.user_serializer_class(
                instance=instance.user,
                data=user_data,
                partial=True,
                context=self.context
            )
            user.is_valid(raise_exception=True)
            user.save()
        return super().update(instance, validated_data)
