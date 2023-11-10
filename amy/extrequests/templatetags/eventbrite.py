from django import template
import regex

from extrequests.utils import get_eventbrite_id_from_url

register = template.Library()

# Eventbrite IDs are long strings of digits (~12 characters)
EVENTBRITE_ID_PATTERN = regex.compile(r"\d{10,}")


@register.simple_tag
def eventbrite_id_from_url(url: str) -> str:
    return get_eventbrite_id_from_url(url)
