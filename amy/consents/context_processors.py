from django.http import HttpRequest

from consents.models import TermEnum, TermOptionChoices


def terms(request: HttpRequest) -> dict:
    return {
        # trick to get Python enum to work in Django templates
        "TermEnum": dict(TermEnum.__members__),
        "TermOptionChoices": TermOptionChoices,
    }
