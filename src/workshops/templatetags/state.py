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
        "p": "badge text-bg-warning",
        "a": "badge text-bg-success",
        "d": "badge text-bg-danger",
        "w": "badge text-bg-secondary",
    }
    result = switch[req.state]
    return mark_safe(result)
