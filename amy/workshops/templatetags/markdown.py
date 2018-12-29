from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from markdownx.utils import markdownify

register = template.Library()


@register.filter()
@stringfilter
def mkdown(value):
    return mark_safe(markdownify(value))
