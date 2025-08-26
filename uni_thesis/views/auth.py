from django.contrib.auth.hashers import check_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from drf_spectacular.utils import extend_schema
from mailersend import EmailBuilder, MailerSendClient
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from uni_project import settings
from uni_project.settings import CACHE_TTL
from uni_thesis.models import User, Student, Professor
from rest_framework.generics import CreateAPIView, GenericAPIView, get_object_or_404
from uni_thesis.serializers import UserCreateSerializer
from uni_thesis.serializers.auth import ChangePasswordRequestSerializer, ChangePasswordActionSerializer


@extend_schema(tags=["authentication"])
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

@extend_schema(tags=["authentication"])
class PasswordResetRequest(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ChangePasswordRequestSerializer

    def post(self, request: Request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, email=serializer.validated_data["email"])
        reset_token = PasswordResetTokenGenerator().make_token(user)
        try:
            cache.set(reset_token, user.id, CACHE_TTL)
            ms = MailerSendClient(api_key=settings.MAILERSEND_API_KEY)

            email = (EmailBuilder()
                     .from_email("no-reply@test-68zxl27zop34j905.mlsender.net", "uni_thesis") # Change to your verified sender
                     .to_many([{"email": user.email, "name": f"{user.first_name} {user.last_name}"}])
                     .subject("Password Reset Code")
                     .html(f"<p>Your reset password code is: <b>{reset_token}</b></p>")
                     .text(f"Your reset password code is: {reset_token}")
                     .build())

            response = ms.emails.send(email)
            print(response)

            if response and hasattr(response, "message_id"):
                return Response("Reset token was emailed successfully!", status=status.HTTP_200_OK)
            else:
                return Response({"error": "Failed to send email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            error_message = {'error': str(e)}
            return Response(error_message, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["authentication"])
class PasswordResetAction(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ChangePasswordActionSerializer

    def put(self, request: Request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.validated_data["reset_token"]
        if not cache.get(reset_token):
            return Response("reset token is wrong or expired!", status.HTTP_400_BAD_REQUEST)
        else:
            user_id = cache.get(reset_token)
            user = get_object_or_404(User, id=user_id)
            new_pass = serializer.validated_data["new_pass"]
            if check_password(new_pass, user.password):
                return Response("New password is same as current password!", status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data["new_pass"])
            user.save()
            return Response("password was changed successfully", status.HTTP_200_OK)