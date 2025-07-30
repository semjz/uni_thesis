from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrOwnStudentOrProfessorReadOnly(BasePermission):
    """
    Allows:
    - Admins full access
    - Professors read-only access to all students
    - Students can access only their own object (view/update)
    - Only Admins can create or delete
    """

    def has_permission(self, request, view):
        user = request.user
        method = request.method
        role = getattr(user, "role", None)

        # Allow Admins everything
        if user.is_staff or user.is_superuser or role == "Admin":
            return True

        # Professors: only read allowed
        if role == "Professor" and method in SAFE_METHODS:
            return True

        # Students: deny POST
        if role == "Student" and method == "POST":
            return False

        # All other users: deny POST/DELETE
        if method in ['POST', 'DELETE']:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        method = request.method
        role = getattr(user, "role", None)

        # Admins can do anything
        if user.is_superuser or user.is_staff or role == "Admin":
            return True

        # Professors can only read
        if method in SAFE_METHODS and role == "Professor":
            return True

        print(role)
        # Students can read/update their own data
        if role == "Student" and method in SAFE_METHODS + ('PUT', 'PATCH'):
            return obj.user == user

        # Deny everything else
        return False
