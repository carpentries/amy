from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def navbar_element(context, title, url_name):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a URL name (with no arguments) that
    is later reversed into proper URL.
    """
    url = reverse(url_name)
    return navbar_element_url(context, title, url)


@register.simple_tag(takes_context=True)
def navbar_element_url(context, title, url):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a pre-made URL as an argument.
    """
    request = context['request']

    active = ""
    screen_reader = ""

    if request.path == url:
        active = 'class="active"'
        screen_reader = '<span class="sr-only">(active)</span>'
    tmplt = '<li {0}><a href="{1}">{2} {3}</a></li>'

    return tmplt.format(active, url, title, screen_reader)
