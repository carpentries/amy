from . import __version__


def version(request):
    return {'workshops_version': __version__}
