from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet
from uni_thesis.models import Professor
from uni_thesis.serializers import ProfessorUpdateSerializer
from uni_thesis.permissions import IsAdminOrOwnProfessorReadOnly
from rest_framework.permissions import IsAuthenticated

@extend_schema(tags=["professors"])
class ProfessorViewSet(ModelViewSet):
    http_method_names = ['get', 'put', 'patch', 'head', 'options']
    permission_classes = [IsAuthenticated, IsAdminOrOwnProfessorReadOnly]
    lookup_field = 'pk'

    def get_serializer_class(self, *args, **kwargs):
        return ProfessorUpdateSerializer

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, "role", None)

        if user.is_superuser or user.is_staff or role == "Admin":
            return Professor.objects.all()

        if role == "Professor":
            return Professor.objects.filter(user__id=user.id)  # Or apply filtering by department, etc.

        return Professor.objects.none()
