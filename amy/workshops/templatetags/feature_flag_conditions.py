from django import template
from flags.sources import Flag

register = template.Library()


@register.simple_tag
def first_parameter_condition(flag: Flag):
    return next((c for c in flag.conditions if c.condition == "parameter"), None)


@register.filter
def url_strip_param_value(url: str):
    try:
        value, *_ = url.split("=")
    except ValueError:
        value = url
    return value
