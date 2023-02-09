from django.http import HttpRequest

from amy import __version__


def version(request: HttpRequest) -> dict:
    data = {"amy_version": __version__}
    return data
