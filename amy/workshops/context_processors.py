from django.conf import settings
from django.http import HttpRequest

from amy import __version__


def version(request: HttpRequest) -> dict:
    data = {"amy_version": __version__}
    return data


def site_banner(request: HttpRequest) -> dict:
    data = {"SITE_BANNER_STYLE": settings.SITE_BANNER_STYLE}
    return data
