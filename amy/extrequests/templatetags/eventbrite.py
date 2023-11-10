from django import template

from extrequests.utils import get_eventbrite_id_from_url

register = template.Library()


@register.simple_tag
def eventbrite_id_from_url(url: str) -> str:
    return get_eventbrite_id_from_url(url)
