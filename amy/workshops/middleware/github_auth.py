from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from workshops.github_auth import NoPersonAssociatedWithGithubAccount


class GithubAuthMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, NoPersonAssociatedWithGithubAccount):
            messages.error(request, "No account is associated with your GitHub account.")
            return redirect(reverse("login"))
