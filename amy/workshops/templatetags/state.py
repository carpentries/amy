from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def state_label(req):
    assert hasattr(req, "state")
    switch = {
        "p": "badge bg-warning",
        "a": "badge bg-success",
        "d": "badge bg-danger",
        "w": "badge bg-secondary",
    }
    result = switch[req.state]
    return mark_safe(result)
