from django.urls import path, include
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.routers import DefaultRouter
from .views import (StudentViewSet, ProfessorViewSet, RegisterAPIView, PasswordResetRequest,
                    PasswordResetAction, CreateThesisDefenceRequestView, MyTimeSlotListCreateView,
                    MyTimeSlotDeleteView, StudentThesisDefenceRequestView, DefenceSessionListView,
                    DefenceSessionDetailAdminView)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)



router = DefaultRouter()
router.register('students', StudentViewSet, basename='student')
router.register('professors', ProfessorViewSet, basename='professor')

app_name = 'uni_thesis'

# Apply schema metadata to POST method
decorated_token_view = extend_schema_view(
    post=extend_schema(
        tags=["authentication"],
        description="Obtain JWT access and refresh tokens."
    )
)(TokenObtainPairView)

decorated_token_refresh_view = extend_schema_view(
    post=extend_schema(
        tags=["authentication"],
        description="Refresh your JWT access token using a refresh token."
    )
)(TokenRefreshView)

urlpatterns = [
    path('', include(router.urls)),

    path('register/', RegisterAPIView.as_view(), name="register"),
    path("change-password-request/", PasswordResetRequest.as_view(), name="reset-password-request"),
    path("change-password-action/", PasswordResetAction.as_view(), name="reset-password-action"),
    path('token/', decorated_token_view.as_view(), name="login"),
    path('token/refresh/', decorated_token_refresh_view.as_view(), name="refresh"),

    # GET/POST  /api/timeslots/
    path("timeslots/", MyTimeSlotListCreateView.as_view(), name="timeslot-list-create"),

    # DELETE    /api/timeslots/<pk>/
    path("timeslots/<int:pk>/", MyTimeSlotDeleteView.as_view(), name="timeslot-delete"),

    path("students/<int:student_id>/thesis-defence-request/",StudentThesisDefenceRequestView.as_view() ,name="student-thesis-defence-request"),

   path("defence-request/<int:student_id>/create/", CreateThesisDefenceRequestView.as_view(), name="thesis-defence-create"),

    path("defence-sessions/", DefenceSessionListView.as_view(), name="defence-session-list"),
    path("defence-sessions/<int:pk>/", DefenceSessionDetailAdminView.as_view(), name="defence-session-detail"),
]