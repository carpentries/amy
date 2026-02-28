from collections.abc import Mapping
from typing import Any

from django import template
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.filter
def one2one_exists(obj: Any, related_field_name: str) -> bool | Any:
    """Check if 1-to-1 related field exists."""
    try:
        obj = getattr(obj, related_field_name)
        return obj
    except ObjectDoesNotExist:
        return False


@register.filter
def get_key(obj: Mapping[str, Any], keyname: str) -> Any:
    """Simply return key from sequence."""
    return obj[keyname]


@register.filter
def is_list(obj: Any) -> bool:
    """Check if provided object is a list."""
    return isinstance(obj, list)
