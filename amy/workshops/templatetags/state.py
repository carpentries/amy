from django import template
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
def state_label(req):
    assert hasattr(req, "state")
    switch = {
        "p": "badge badge-warning",
        "a": "badge badge-success",
        "d": "badge badge-danger",
    }
    result = switch[req.state]
    return mark_safe(result)
