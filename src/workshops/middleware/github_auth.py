from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from src.workshops.github_auth import NoPersonAssociatedWithGithubAccount


class GithubAuthMiddleware(MiddlewareMixin):
    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse | None:
        if isinstance(exception, NoPersonAssociatedWithGithubAccount):
            messages.error(request, "No account is associated with your GitHub account.")
            return redirect(reverse("login"))
        return None
