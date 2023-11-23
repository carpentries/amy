import re

from django import template

from extrequests.utils import EVENTBRITE_URL_PATTERN

register = template.Library()


@register.simple_tag
def url_matches_eventbrite_format(url: str) -> bool:
    match = re.search(EVENTBRITE_URL_PATTERN, url)
    return match is not None
