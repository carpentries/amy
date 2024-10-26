from django import template
from flags.sources import Condition, Flag

register = template.Library()


@register.simple_tag
def first_parameter_condition(flag: Flag) -> Condition | None:
    return next((c for c in flag.conditions if c.condition == "parameter"), None)


@register.simple_tag
def can_change_state(flag: Flag) -> bool:
    return any(c.condition == "parameter" for c in flag.conditions)


@register.filter
def parameter_strip_value(url: str) -> str:
    try:
        value, *_ = url.split("=")
    except ValueError:
        value = url
    return value
