from django import template
# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def bootstrap_tag(name):
    """Wrap <span> around a tag so that it's displayed as Bootstrap badge:
    http://getbootstrap.com/components/#labels"""

    addn_class = 'badge-secondary'
    if name == 'SWC':
        addn_class = 'badge-primary'
    elif name == 'DC':
        addn_class = 'badge-success'
    elif name == 'online':
        addn_class = 'badge-info'
    elif name == 'LC':
        addn_class = 'badge-warning'

    fmt = '<span class="badge {additional_class}">{name}</span>'
    fmt = fmt.format(additional_class=addn_class, name=name)
    return mark_safe(fmt)
