from datetime import date, datetime

from django import template
from django.utils.safestring import SafeString, mark_safe

from src.workshops.utils.dates import human_daterange as human_daterange_util

register = template.Library()


@register.simple_tag
def human_daterange(date_left: date | datetime | None, date_right: date | datetime | None) -> SafeString:
    result = human_daterange_util(date_left, date_right)
    return mark_safe(result)
