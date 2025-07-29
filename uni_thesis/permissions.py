from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrOwnStudentOrProfessorReadOnly(BasePermission):
    """
    Allows:
    - Admins full access
    - Professors read-only access to all students
    - Students access only to their own student object (view/update)
    - No one except Admins can delete
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admins and superusers can do anything
        if user.is_superuser or user.is_staff or getattr(user, "role", None) == "Admin":
            return True

        # Professors can only read
        if request.method in SAFE_METHODS and getattr(user, "role", None) == "Professor":
            return True

        # Students can only read/update their own object
        if getattr(user, "role", None) == "Student":
            if request.method in SAFE_METHODS or request.method in ['PUT', 'PATCH']:
                return obj.user == user  # assumes Student has OneToOne to User

        # Deny DELETE for everyone else
        return False