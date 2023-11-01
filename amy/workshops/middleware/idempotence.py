from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin


class IdempotenceMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest) -> HttpRequest | None:
        if not request.method == "POST":
            return None

        # get idempotence token and compare with session cache
        token = request.POST.get("idempotence_token")
        if cache := request.session.get("idempotence_token_cache"):
            # if this token has already been used,
            # return the same response without taking any further action
            if token in cache:
                messages.info(
                    request,
                    f"Found duplicate POST request for token {token}, "
                    "returning cached response",
                )
                return HttpResponse()
        else:
            # no cache exists for this session, so create one
            request.session["idempotence_token_cache"] = []

        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        # put this response into idempotence cache if needed
        if request.method == "POST":
            token = request.POST.get("idempotence_token")
            cache = request.session.get("idempotence_token_cache")
            if token and token not in cache:
                request.session["idempotence_token_cache"].append(token)

        return response
