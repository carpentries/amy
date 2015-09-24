from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import urlize as urlize
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(is_safe=True, needs_autoescape=True)
@stringfilter
def urlize_newtab(value, autoescape=True):
    "Converts URLs in plain text into clickable links that open in new tabs."
    url = urlize(value, nofollow=True, autoescape=autoescape)
    url = url.replace('a href', 'a target="_blank" href')
    return mark_safe(url)
