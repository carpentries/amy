from . import __version__


def version(request):
    data = {'amy_version': __version__}
    return data
