import json
import pprint as stdlib_pprint
from typing import Any

from django import template

register = template.Library()


@register.filter
def indent_json(value: Any, indent: int = 2) -> str:
    """Indent string containing JSON."""
    return json.dumps(value, sort_keys=True, indent=indent)


@register.filter
def pprint_py(value: Any) -> str:
    """Indent Python dict."""
    return stdlib_pprint.pformat(value, width=40)
