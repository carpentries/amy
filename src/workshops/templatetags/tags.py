from django import template

# from django.template.defaultfilters import stringfilter
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@register.simple_tag
def bootstrap_tag_class(name: str) -> SafeString:
    name_low = name.lower()

    mapping = {
        "swc": "badge-primary",
        "dc": "badge-success",
        "online": "badge-info",
        "lc": "badge-warning",
        "ttt": "badge-danger",
        "itt": "badge-danger",
        "instructor": "badge-primary",
        "trainer": "badge-dark",
    }
    default = "badge-secondary"

    return mark_safe(
        next(
            (css_class for prefix, css_class in mapping.items() if name_low.startswith(prefix)),
            default,
        )
    )


@register.simple_tag
def bootstrap_tag(name: str) -> SafeString:
    """Wrap <span> around a tag so that it's displayed as Bootstrap badge:
    http://getbootstrap.com/components/#labels"""
    addn_class = bootstrap_tag_class(name)

    fmt = '<span class="badge {additional_class}">{name}</span>'
    fmt = fmt.format(additional_class=addn_class, name=name)
    return mark_safe(fmt)
