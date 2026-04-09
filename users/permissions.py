from rest_framework.permissions import BasePermission

class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["admin", "manager"]
# permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrManagerOrReadOnlyReviewer(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", None)

        # ✅ Admin & Manager → full access
        if role in ["admin", "manager"]:
            return True

        # ✅ Reviewer → read only
        if role == "reviewer":
            return request.method in SAFE_METHODS

        return False

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "role", None)

        if role in ["admin", "manager"]:
            return True

        if role == "reviewer":
            return request.method in SAFE_METHODS

        return False