from django import template
from django.utils.safestring import mark_safe

from reversion.helpers import generate_patch_html

register = template.Library()


@register.simple_tag
def semantic_diff(left, right, field):
    return mark_safe(generate_patch_html(left, right, field, cleanup='semantic'))
