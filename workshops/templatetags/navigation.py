from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def navbar_element(context, title, url_name):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.
    """
    request = context['request']
    url = reverse(url_name)

    active = ""
    screen_reader = ""

    if request.path == url:
        active = 'class="active"'
        screen_reader = '<span class="sr-only">(active)</span>'
    tmplt = '<li {0}><a href="{1}">{2} {3}</a></li>'

    return tmplt.format(active, url, title, screen_reader)
