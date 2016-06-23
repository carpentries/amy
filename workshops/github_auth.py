from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from social.exceptions import SocialAuthBaseException

from workshops.models import Person


class NoPersonAssociatedWithGithubAccount(SocialAuthBaseException):
    pass


def find_user_or_abort(details=None, **kwargs):
    username = details['username']
    try:
        user = Person.objects.get(github=username, is_active=True)
        return {'user': user}
    except Person.DoesNotExist:
        # This exception is caught by GithubAuthMiddleware
        raise NoPersonAssociatedWithGithubAccount


class GithubAuthMiddleware():
    def process_exception(self, request, exception):
        if isinstance(exception, NoPersonAssociatedWithGithubAccount):
            messages.error(request,
                           'No account is associated with your GitHub account.')
            return redirect(reverse('login'))
