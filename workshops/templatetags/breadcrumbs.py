import logging

from django import template
from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.utils.html import escape

register = template.Library()
_LOG = logging.getLogger(__name__)


@register.simple_tag
def breadcrumb(title, url):
    '''
    Create a simple anchor with provided text and already-resolved URL.
    Example usage:
        {% breadcrumb "Title of breadcrumb" resolved_url %}
    '''
    return create_crumb(title, url)


@register.simple_tag
def breadcrumb_url(title, url_name):
    '''
    Add non-active breadcrumb with specified title.  Second argument should be
    a string name of URL that needs to be resolved.
    Example usage:
        {% breadcrumb_url "Title of breadcrumb" url_name %}
    '''
    url = reverse(url_name)
    return create_crumb(title, url)


@register.simple_tag
def breadcrumb_active(title):
    '''
    Add active breadcrumb, but not in an anchor.
    Example usage:
        {% breadcrumb_active "Title of breadcrumb" %}
    '''
    return create_crumb(title, url=None, active=True)


@register.simple_tag
def breadcrumb_index_all_objects(model):
    '''
    Add breadcrumb linking to the listing of all objects of specific type.
    This tag accepts both models or model instances as an argument.
    Example usage:
        {% breadcrumb_index_all_objects model %}
        {% breadcrumb_index_all_objects person %}
    '''
    plural = force_text(model._meta.verbose_name_plural)
    title = 'All {}'.format(plural)
    url_name = 'all_{}'.format(plural)
    url = reverse(url_name)
    return create_crumb(title, url)


@register.simple_tag
def breadcrumb_edit_object(obj):
    '''
    Add an active breadcrumb with the title "Edit MODEL_NAME".
    This tag accepts model instance as an argument.
    Example usage:
        {% breadcrumb_edit_object person %}
    '''
    singular = force_text(obj._meta.verbose_name)
    title = 'Edit {}'.format(singular)
    return create_crumb(title, url=None, active=True)


@register.simple_tag
def breadcrumb_new_object(model):
    '''
    Add an active breadcrumb with the title "Add new MODEL_NAME".
    This tag accepts model class as an argument.
    Example usage:
        {% breadcrumb_new_object person %}
    '''
    singular = force_text(model._meta.verbose_name)
    title = 'Add new {}'.format(singular)
    return create_crumb(title, url=None, active=True)


@register.simple_tag
def breadcrumb_object(obj):
    '''
    Add non-active breadcrumb with the title "Add new MODEL_NAME".
    This tag accepts model instance as an argument.
    Example usage:
        {% breadcrumb_object person %}
    '''
    title = str(obj)
    url = obj.get_absolute_url()
    return create_crumb(title, url, active=False)


@register.simple_tag
def breadcrumb_main_page():
    '''
    Special case of ``breadcrumb_url``.  In all templates there's always a link
    to the main page so I wanted to save everyone thinking & writing by
    introducing this helper tag.
    Example usage:
        {% breadcrumb_main_page %}
    '''
    title = 'Amy'
    url = reverse('index')
    return create_crumb(title, url)


def create_crumb(title, url=None, active=False):
    '''
    Helper function that creates breadcrumb.
    '''
    active_str = ''
    if active:
        active_str = ' class="active"'

    title = escape(title)
    inner_str = title
    if url:
        inner_str = '<a href="{0}">{1}</a>'.format(url, title)

    crumb = '<li{0}>{1}</li>'.format(active_str, inner_str)

    return crumb
