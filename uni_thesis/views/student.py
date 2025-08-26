from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet
from uni_thesis.models import Student
from uni_thesis.serializers import StudentUpdateSerializer
from uni_thesis.permissions import IsAdminOrOwnStudentOrProfessorReadOnly
from rest_framework.permissions import IsAuthenticated

@extend_schema(tags=["students"])
class StudentViewSet(ModelViewSet):
    http_method_names = ['get', 'put', 'patch', 'head', 'options']
    queryset = Student.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrOwnStudentOrProfessorReadOnly]
    lookup_field = 'pk'

    def get_serializer_class(self, *args, **kwargs):
        return StudentUpdateSerializer

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, "role", None)

        if user.is_superuser or user.is_staff or role == "Admin":
            return Student.objects.all()

        if role == "Professor":
            return Student.objects.all()  # Or apply filtering by department, etc.

        if role == "Student":
            return Student.objects.filter(user__id=user.id)

        return Student.objects.none()
