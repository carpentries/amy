from . import __version__
try:
    from . import git_version
except ImportError:
    git_version = None


def version(request):
    data = {'workshops_version': __version__}
    if git_version:
        data.update({
            'workshops_git_hash': git_version.HASH,
            'workshops_git_short_hash': git_version.SHORT_HASH,
            'workshops_git_date': git_version.DATE,
            'workshops_git_dirty': git_version.DIRTY,
        })
    return data
