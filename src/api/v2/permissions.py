from rest_framework.permissions import BasePermission


class ApiAccessPermission(BasePermission):
    _permission_name = "knox.add_authtoken"

    def has_permission(self, request, view):
        return request.user.has_perm(self._permission_name)
