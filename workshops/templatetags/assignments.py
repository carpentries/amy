from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def assign(variable):
    """Directly pass a variable to the output.

    This tag is intended to use with the new 'as' syntax:
    {% assign "123" as number %}"""
    return mark_safe(variable)
