from django import template
import regex

register = template.Library()

# Eventbrite IDs are long strings of digits (~12 characters)
EVENTBRITE_ID_PATTERN = regex.compile(r"\d{10,}")


@register.simple_tag
def eventbrite_id_from_url(url: str) -> str:
    if not isinstance(url, str):
        return url

    re = regex.search(EVENTBRITE_ID_PATTERN, url)
    return re.group() if re else url
