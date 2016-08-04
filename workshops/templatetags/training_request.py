from django import template
from django.utils.safestring import mark_safe

from workshops.models import TrainingRequest

register = template.Library()


@register.simple_tag
def training_request_label(req):
    assert isinstance(req, TrainingRequest)
    switch = {
        'p': 'label label-warning',
        'a': 'label label-success',
        'd': 'label label-danger',
    }
    result = switch[req.state]
    return mark_safe(result)
