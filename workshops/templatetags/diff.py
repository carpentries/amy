from django import template

from reversion.helpers import generate_patch_html

register = template.Library()


@register.simple_tag
def semantic_diff(left, right, field):
    return generate_patch_html(left, right, field, cleanup='semantic')
