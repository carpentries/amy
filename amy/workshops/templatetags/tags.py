from django import template

# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def bootstrap_tag_class(name):
    name_low = name.lower()

    class_ = "badge-secondary"
    if name_low.startswith("swc"):
        class_ = "badge-primary"
    elif name_low.startswith("dc"):
        class_ = "badge-success"
    elif name_low.startswith("online"):
        class_ = "badge-info"
    elif name_low.startswith("lc"):
        class_ = "badge-warning"
    elif name_low.startswith("ttt"):
        class_ = "badge-danger"
    elif name_low.startswith("itt"):
        class_ = "badge-danger"

    return mark_safe(class_)


@register.simple_tag
def bootstrap_tag(name):
    """Wrap <span> around a tag so that it's displayed as Bootstrap badge:
    http://getbootstrap.com/components/#labels"""
    addn_class = bootstrap_tag_class(name)

    fmt = '<span class="badge {additional_class}">{name}</span>'
    fmt = fmt.format(additional_class=addn_class, name=name)
    return mark_safe(fmt)
