from django import template

register = template.Library()


@register.filter
def split(value, separator=","):
    """Split text into list using provided separator (a comma by default)."""
    if value:
        return value.split(separator)
    return []


@register.filter
def strip(value):
    """Strip string."""
    return value.strip()
