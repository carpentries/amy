from typing import cast

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import SafeString, mark_safe
from markdownx.utils import markdownify

register = template.Library()


@register.filter()
@stringfilter
def mkdown(value: str) -> SafeString:
    return mark_safe(cast(str, markdownify(value)))  # type: ignore[no-untyped-call]
