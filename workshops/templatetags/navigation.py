from django import template
from django.core.urlresolvers import reverse

register = template.Library()


def make_element(title, url, active=False, disabled=False):
    screen_reader = ''
    classes = []

    if disabled:
        classes.append('disabled')

    if active:
        classes.append('active')
        screen_reader = '<span class="sr-only">(active)</span>'

    if classes:
        classes = ' '.join(classes)
        template = ('<li class="{classes}"><a href="{url}">{title} '
                    '{screen_reader}</a></li>')
        return template.format(classes=classes, url=url, title=title,
                               screen_reader=screen_reader)
    else:
        template = ('<li><a href="{url}">{title}</a></li>')
        return template.format(url=url, title=title)


@register.simple_tag(takes_context=True)
def navbar_element(context, title, url_name):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a URL name (with no arguments) that
    is later reversed into proper URL.
    """
    url = reverse(url_name)
    active = context['request'].path == url
    return make_element(title, url, active=active)


@register.simple_tag(takes_context=True)
def navbar_element_permed(context, title, url_name, perms):
    """
    Works like `navbar_element`, but also disables if user doesn't have
    permissions.

    `perms` can be a comma-separated string of permissions or a single
    permission.
    """
    url = reverse(url_name)
    active = context['request'].path == url
    disabled = True

    # check permissions
    perms_ctx = context['perms']
    perms = perms.split(',')
    perms = map(lambda x: x in perms_ctx, perms)
    if all(perms):
        disabled = False

    return make_element(title, url, active=active, disabled=disabled)


@register.simple_tag(takes_context=True)
def navbar_element_url(context, title, url):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a pre-made URL as an argument.
    """
    active = context['request'].path == url
    return make_element(title, url, active=active)
