from django import template
# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def bootstrap_tag(name):
    """Wrap <span> around a tag so that it's displayed as Bootstrap badge:
    http://getbootstrap.com/components/#labels"""

    name_low = name.lower()

    addn_class = 'badge-secondary'
    if name_low.startswith('swc'):
        addn_class = 'badge-primary'
    elif name_low.startswith('dc'):
        addn_class = 'badge-success'
    elif name_low.startswith('online'):
        addn_class = 'badge-info'
    elif name_low.startswith('lc'):
        addn_class = 'badge-warning'
    elif name_low.startswith('ttt'):
        addn_class = 'badge-danger'

    fmt = '<span class="badge {additional_class}">{name}</span>'
    fmt = fmt.format(additional_class=addn_class, name=name)
    return mark_safe(fmt)
