from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import SafeString

from src.workshops.utils.markdown import render_markdown

register = template.Library()


@register.filter()
@stringfilter
def mkdown(value: str) -> SafeString:
    return render_markdown(value)
