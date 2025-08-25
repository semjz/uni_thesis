from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from uni_thesis.models import User, Student, Professor
from rest_framework.generics import CreateAPIView
from uni_thesis.serializers import UserCreateSerializer


class RegisterAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user_data = response.data
        user_id = user_data["id"]
        role = user_data["role"]

        user = User.objects.get(id=user_id)

        if role == "Student":
            s = Student.objects.create(user=user)
            user_data["id"] = s.id
        elif role == "Professor":
            p = Professor.objects.create(user=user)
            user_data["id"] = p.id



        return Response({
            "user": user_data,
        }, status=status.HTTP_201_CREATED)