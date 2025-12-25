from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from src.workshops.context_processors import read_version_from_toml


class VersionCheckMiddleware(MiddlewareMixin):
    """To work around issues with ALLOWED_HOSTS and load balancer pinging Django,
    this middleware is run before ALLOWED_HOSTS kicks in."""

    def process_request(self, request):
        if request.META["PATH_INFO"] == "/version/":
            return HttpResponse(read_version_from_toml())
