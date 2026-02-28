from typing import Any

from django.http import HttpRequest

from src.consents.models import TermEnum, TermOptionChoices


def terms(request: HttpRequest) -> dict[str, Any]:
    return {
        # trick to get Python enum to work in Django templates
        "TermEnum": dict(TermEnum.__members__),
        "TermOptionChoices": TermOptionChoices,
    }
