from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from amy import __version__


class VersionCheckMiddleware(MiddlewareMixin):
    """To work around issues with ALLOWED_HOSTS and load balancer pinging Django,
    this middleware is run before ALLOWED_HOSTS kicks in."""

    def process_request(self, request):
        if request.META["PATH_INFO"] == "/version/":
            return HttpResponse(str(__version__))
