from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register('students', StudentViewSet, basename='student')

app_name = 'uni_thesis'

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='refresh'),
]