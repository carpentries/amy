from typing import Protocol

from django import template
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


class StateProtocol(Protocol):
    state: str


@register.simple_tag
def state_label(req: StateProtocol) -> SafeString:
    assert hasattr(req, "state")
    switch = {
        "p": "badge badge-warning",
        "a": "badge badge-success",
        "d": "badge badge-danger",
        "w": "badge badge-secondary",
    }
    result = switch[req.state]
    return mark_safe(result)
