from django import template
# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


# @register.filter(is_safe=True, needs_autoescape=True)
# @stringfilter
@register.simple_tag
def bootstrap_tag(name):
    """Wrap <span> around a tag so that it's displayed as Bootstrap label:
    http://getbootstrap.com/components/#labels"""

    addn_class = 'label-default'
    if name == 'SWC':
        addn_class = 'label-primary'
    elif name == 'DC':
        addn_class = 'label-success'
    elif name == 'online':
        addn_class = 'label-info'
    elif name == 'LC':
        addn_class = 'label-warning'

    fmt = '<span class="label {additional_class}">{name}</span>'
    fmt = fmt.format(additional_class=addn_class, name=name)
    return mark_safe(fmt)
