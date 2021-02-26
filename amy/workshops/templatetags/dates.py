from django import template
from django.utils.safestring import mark_safe

from workshops.util import human_daterange as human_daterange_util

register = template.Library()


@register.simple_tag
def human_daterange(date_left, date_right):
    result = human_daterange_util(date_left, date_right)
    return mark_safe(result)
