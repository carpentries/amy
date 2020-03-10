from urllib.parse import urljoin

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from github import Github
from github.GithubException import UnknownObjectException
from social_core.backends.github import GithubOAuth2
from social_core.exceptions import SocialAuthBaseException

from workshops.fields import (
    GHUSERNAME_MAX_LENGTH_VALIDATOR,
    GHUSERNAME_REGEX_VALIDATOR,
)


class NoPersonAssociatedWithGithubAccount(SocialAuthBaseException):
    pass


def abort_if_no_user_found(user=None, **kwargs):
    """Part of Python-Social pipeline; aborts the authentication if no user
    can be associated with the specified GitHub username."""
    if user is None:
        raise NoPersonAssociatedWithGithubAccount


class GithubAuthMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, NoPersonAssociatedWithGithubAccount):
            messages.error(request,
                           'No account is associated with your GitHub account.')
            return redirect(reverse('login'))


def github_username_to_uid(username):
    """Return UID (int) of GitHub account for username == `Person.github`.

    WARNING: this should only accept valid usernames (use
    `validate_github_username` before invoking this function)."""

    g = Github(settings.GITHUB_API_TOKEN)

    try:
        user = g.get_user(username)

    except UnknownObjectException as e:
        msg = 'There is no github user with login "{}"'.format(username)
        raise ValueError(msg) from e

    except IOError as e:
        msg = 'Impossible to check username due to IO errors.'
        raise ValueError(msg) from e

    else:
        return user.id


def validate_github_username(username):
    """Run GitHub username validators in sequence."""
    GHUSERNAME_MAX_LENGTH_VALIDATOR(username)
    GHUSERNAME_REGEX_VALIDATOR(username)


class GithubOAuth2HeaderFix(GithubOAuth2):
    """
    Hotfix Github OAuth backend to use basic auth instead of token.

    Borrowed from:
    https://github.com/python-social-auth/social-core/pull/428
    https://github.com/python-social-auth/social-core/pull/428#issuecomment-594085060
    """

    def _user_data(self, access_token, path=None):
        url = urljoin(self.api_url(), 'user{0}'.format(path or ''))
        headers = {'Authorization': 'token {0}'.format(access_token)}
        return self.get_json(url, headers=headers)
