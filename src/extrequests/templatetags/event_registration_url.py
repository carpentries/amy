import re

from django import template

from src.extrequests.utils import EVENTBRITE_URL_PATTERN, PRETIX_URL_PATTERN

register = template.Library()


@register.simple_tag
def url_matches_eventbrite_or_pretix_format(url: str) -> bool:
    match1 = re.search(EVENTBRITE_URL_PATTERN, url)
    match2 = re.search(PRETIX_URL_PATTERN, url)
    return match1 is not None or match2 is not None
