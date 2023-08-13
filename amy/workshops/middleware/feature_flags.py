from django.http import HttpRequest
from flags.sources import get_flags


class SaveSessionFeatureFlagMiddleware:
    """Save a feature flag value to the session if it was set in the request and the
    respective condition was met."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        flags = get_flags(request=request)
        parameter_conditions = [
            condition
            for flag_name, flag in flags.items()
            for condition in flag.conditions
            if condition.condition == "parameter"
        ]

        for parameter_condition in parameter_conditions:
            if parameter_condition.check(request=request):
                value, *_ = parameter_condition.value.split("=")
                request.session[value] = True

        return self.get_response(request)
