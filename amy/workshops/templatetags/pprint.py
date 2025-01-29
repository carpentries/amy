import json
from typing import Any

from django import template

register = template.Library()


@register.filter
def indent_json(value: Any, indent: int = 2) -> str:
    """Indent string containing JSON."""
    return json.dumps(value, sort_keys=True, indent=indent)
