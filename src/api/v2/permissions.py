from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class ApiAccessPermission(BasePermission):
    _permission_name = "knox.add_authtoken"

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.has_perm(self._permission_name)
