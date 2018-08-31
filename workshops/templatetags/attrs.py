from django import template
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.filter
def one2one_exists(obj, related_field_name):
    """Check if 1-to-1 related field exists."""
    try:
        obj = getattr(obj, related_field_name)
        return obj
    except ObjectDoesNotExist:
        return False
