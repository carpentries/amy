from django import template

register = template.Library()


@register.filter
def split(value: str, separator: str = ",") -> list[str]:
    """Split text into list using provided separator (a comma by default)."""
    if value:
        return value.split(separator)
    return []


@register.filter
def strip(value: str) -> str:
    """Strip string."""
    return value.strip()
