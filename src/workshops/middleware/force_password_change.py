from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_anonymous or not request.user.force_password_change_on_login:
            return self.get_response(request)

        url = reverse("person_password", args=[request.user.pk])

        # Terms page is allowed, otherwise this middleware and TermsMiddleware
        # would redirect to each other indefinitely.
        allowed_urls = [reverse("logout"), reverse("action_required_terms"), url]

        if request.path in allowed_urls:
            return self.get_response(request)

        # prepare `?next` URL if it's already present (e.g. user refreshes
        # the password change page)
        next_param = request.GET.get("next", request.path)

        # only add `?next` if it's outside the scope of allowed URLs
        if next_param not in allowed_urls:
            url += "?{}".format(urlencode({"next": next_param}))

        return redirect(url)
