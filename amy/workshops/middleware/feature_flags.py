from django.http import HttpRequest
from flags.sources import Condition, Flag, get_flags


class SaveSessionFeatureFlagMiddleware:
    """Save a feature flag value to the session if it was set in the request and the
    respective condition was met."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        flags = get_flags(request=request)
        parameter_conditions = self.conditions_of_type(flags, type="parameter")

        for condition in parameter_conditions:
            param_name = self.get_parameter_name_from_condition(condition)

            # set feature flag in session if the conditions are met
            if condition.check(request=request):
                self.enable_feature_flag(request, param_name)

            # disable the feature flag in session of the request parameter is set to
            # "false"
            elif request.session.get(param_name, None) is True and request.GET.get(param_name, "").lower() == "false":
                self.disable_feature_flag(request, param_name)

        return self.get_response(request)

    @staticmethod
    def conditions_of_type(flags: dict[str, Flag], type: str) -> list[Condition]:
        return [
            condition
            for flag_name, flag in flags.items()
            for condition in flag.conditions
            if condition.condition == type
        ]

    @staticmethod
    def get_parameter_name_from_condition(condition: Condition) -> str:
        try:
            param_name, *_ = condition.value.split("=")
        except ValueError:
            param_name = condition.value

        return param_name

    @staticmethod
    def enable_feature_flag(request: HttpRequest, flag_name: str) -> None:
        """Set a feature flag in the session."""
        request.session[flag_name] = True

    @staticmethod
    def disable_feature_flag(request: HttpRequest, flag_name: str) -> None:
        """Set a feature flag in the session."""
        request.session[flag_name] = False
