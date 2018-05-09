from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from github import Github
from github.GithubException import UnknownObjectException
from social_core.exceptions import SocialAuthBaseException


class NoPersonAssociatedWithGithubAccount(SocialAuthBaseException):
    pass


def abort_if_no_user_found(user=None, **kwargs):
    if user is None:
        raise NoPersonAssociatedWithGithubAccount


class GithubAuthMiddleware():
    def process_exception(self, request, exception):
        if isinstance(exception, NoPersonAssociatedWithGithubAccount):
            messages.error(request,
                           'No account is associated with your GitHub account.')
            return redirect(reverse('login'))


def github_username_to_uid(username):
    """ Returns int.

    Raises ValueError if there is no user with given username.

    Raises GithubException in the case of IO issues."""

    g = Github(settings.GITHUB_API_TOKEN)

    # Github.get_user(username) is buggy and raises ConnectionResetError when
    # username contains spaces (see #1141). Spaces in GitHub usernames are
    # forbidden, so we safely assume that there is no user with a space in their
    # username.
    if ' ' in username:
        msg = 'There is no github user with login "{}"'.format(username)
        raise ValueError(msg)

    try:
        user = g.get_user(username)
    except UnknownObjectException as e:
        msg = 'There is no github user with login "{}"'.format(username)
        raise ValueError(msg) from e
    else:
        return user.id
