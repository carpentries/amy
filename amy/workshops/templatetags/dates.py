from django import template
from django.utils.safestring import mark_safe
from django.utils.timezone import now

from workshops.utils.dates import human_daterange as human_daterange_util

register = template.Library()


@register.simple_tag
def human_daterange(date_left, date_right):
    result = human_daterange_util(date_left, date_right)
    return mark_safe(result)


@register.simple_tag
def is_late_in_year():
    """return True if current month is October, November, or December"""

    return now().month >= 10
