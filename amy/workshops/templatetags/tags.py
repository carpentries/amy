from django import template

# from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def bootstrap_tag_class(name):
    name_low = name.lower()

    mapping = {
        "swc": "bg-primary",
        "dc": "bg-success",
        "online": "bg-info",
        "lc": "bg-warning",
        "ttt": "bg-danger",
        "itt": "bg-danger",
        "instructor": "bg-primary",
        "trainer": "bg-dark",
    }
    default = "bg-secondary"

    return mark_safe(
        next(
            (
                css_class
                for prefix, css_class in mapping.items()
                if name_low.startswith(prefix)
            ),
            default,
        )
    )


@register.simple_tag
def bootstrap_tag(name):
    """Wrap <span> around a tag so that it's displayed as Bootstrap badge:
    http://getbootstrap.com/components/#labels"""
    addn_class = bootstrap_tag_class(name)

    fmt = '<span class="badge {additional_class}">{name}</span>'
    fmt = fmt.format(additional_class=addn_class, name=name)
    return mark_safe(fmt)
