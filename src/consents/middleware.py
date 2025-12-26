from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from src.consents.util import person_has_consented_to_required_terms


class TermsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        url = reverse("action_required_terms")

        allowed_urls = [reverse("logout"), url]

        # prepare `?next` URL if it's already present (e.g. user refreshes
        # the `action_required_privacy` page)
        next_param = request.GET.get("next", request.path)

        # only add `?next` if it's outside the scope of allowed URLs
        if next_param not in allowed_urls:
            url += "?{}".format(urlencode({"next": next_param}))

        # redirect only users who didn't agree on the privacy policy
        # also don't redirect if the requested page is the page we want to
        # redirect to
        if (
            request.path not in allowed_urls
            and not request.user.is_anonymous
            and not person_has_consented_to_required_terms(request.user)
        ):
            return redirect(url)
        else:
            return self.get_response(request)
