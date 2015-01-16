import logging

from django import template
from django.template import VariableDoesNotExist
from django.template import loader, Node, Variable
from django.template.defaulttags import url
from django.utils.encoding import smart_text
from django.utils.html import escape

register = template.Library()
_LOG = logging.getLogger(__name__)


@register.tag
def breadcrumb(parser, token):
    """
    Renders the breadcrumb.
    Examples:
        {% breadcrumb "Title of breadcrumb" url_var %}
        {% breadcrumb context_var  url_var %}
        {% breadcrumb "Just the title" %}
        {% breadcrumb just_context_var %}

    Parameters:
    -First parameter is the title of the crumb,
    -Second (optional) parameter is the url variable to link to, produced by
     url tag, i.e.:
        {% url person_detail object.id as person_url %}
        then:
        {% breadcrumb person.name person_url %}

    @author Andriy Drozdyuk
    """
    return BreadcrumbNode(token.split_contents()[1:])


@register.tag
def breadcrumb_url(parser, token):
    """
    Same as breadcrumb
    but instead of url context variable takes in all the
    arguments URL tag takes.
        {% breadcrumb "Title of breadcrumb" person_detail person.id %}
        {% breadcrumb person.name person_detail person.id %}
    """

    bits = token.split_contents()
    if len(bits) == 2:
        return breadcrumb(parser, token)

    # Extract our extra title parameter
    title = bits.pop(1)
    token.contents = ' '.join(bits)

    url_node = url(parser, token)

    return UrlBreadcrumbNode(title, url_node)


@register.simple_tag
def breadcrumb_active(title):
    """
    Same as breadcrumb, but adds "active" CSS class.  Only breadcrumb title is
    supported.
        {% breadcrumb_active "Title of breadcrumb" %}
    """
    return create_crumb(title, active=True)


class BreadcrumbNode(Node):
    def __init__(self, vars):
        """
        First var is title, second var is url context variable
        """
        self.vars = list(map(Variable, vars))

    def render(self, context):
        title = self.vars[0].var

        if title.find("'") == -1 and title.find('"') == -1:
            try:
                val = self.vars[0]
                title = val.resolve(context)
            except:
                title = ''

        else:
            title = title.strip("'").strip('"')
            title = smart_text(title)

        url = None

        if len(self.vars) > 1:
            val = self.vars[1]
            try:
                url = val.resolve(context)
            except VariableDoesNotExist:
                _LOG.warning('URL does not exist {}'.format(val))
                url = None

        return create_crumb(title, url)


class UrlBreadcrumbNode(Node):
    def __init__(self, title, url_node):
        self.title = Variable(title)
        self.url_node = url_node

    def render(self, context):
        title = self.title.var

        if title.find("'") == -1 and title.find('"') == -1:
            try:
                val = self.title
                title = val.resolve(context)
            except:
                title = ''
        else:
            title = title.strip("'").strip('"')
            title = smart_text(title)

        url = self.url_node.render(context)
        return create_crumb(title, url)


def create_crumb(title, url=None, active=False):
    """
    Helper function
    """

    active_str = ""
    if active:
        active_str = ' class="active"'

    title = escape(title)
    inner_str = title
    if url:
        inner_str = '<a href="{0}">{1}</a>'.format(url, title)

    crumb = "<li {0}>{1}</li>".format(active_str, inner_str)

    return crumb
