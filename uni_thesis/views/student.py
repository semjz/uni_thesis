from rest_framework.viewsets import ModelViewSet
from uni_thesis.models import Student
from uni_thesis.serializers import StudentCreateSerializer, StudentUpdateSerializer
from uni_thesis.permissions import IsAdminOrOwnStudentOrProfessorReadOnly
from rest_framework.permissions import IsAuthenticated

class StudentViewSet(ModelViewSet):
    permission_classes = [IsAdminOrOwnStudentOrProfessorReadOnly, IsAuthenticated]
    lookup_field = 'pk'

    def get_serializer_class(self, *args, **kwargs):
        if self.action == 'create':
            return StudentCreateSerializer
        return StudentUpdateSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Student.objects.all()
        return Student.objects.filter(user__id = user.id)
