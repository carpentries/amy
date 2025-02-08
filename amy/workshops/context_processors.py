from django.conf import settings
from django.http import HttpRequest
from flags.sources import get_flags

from amy import __version__


def version(request: HttpRequest) -> dict:
    data = {"amy_version": __version__}
    return data


def site_banner(request: HttpRequest) -> dict:
    data = {"SITE_BANNER_STYLE": settings.SITE_BANNER_STYLE}
    return data


def feature_flags_enabled(request: HttpRequest) -> dict:
    flags = get_flags(request=request)
    data = {"FEATURE_FLAGS_ENABLED": [flag for flag in flags.values() if flag.check_state(request=request) is True]}
    return data
