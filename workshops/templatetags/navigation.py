from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse

register = template.Library()


def navbar_template(title, url, active=False, disabled=False,
                    dropdown=False):
    """Compose Bootstrap v4 <li> element for top navigation bar.

    List item can be added one or more class attributes:
    * active: to highlight currently visited tab
    * disabled: to disable access, for example for users without specific
      permissions.
    """
    screen_reader = ''
    classes = []

    if disabled:
        classes.append('disabled')

    if active:
        classes.append('active')
        screen_reader = mark_safe(' <span class="sr-only">(current)</span>')

    classes = ' '.join(classes)
    template = ('<li class="nav-item {classes}"><a class="nav-link" '
                'href="{url}">{title} {screen_reader}</a></li>')
    if dropdown:
        template = ('<a class="dropdown-item {classes}" href="{url}">'
                    '{title} {screen_reader}</a>')
    return format_html(template, classes=classes, url=url,
                       title=title, screen_reader=screen_reader)


@register.simple_tag(takes_context=True)
def navbar_element(context, title, url_name, dropdown=False):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a URL name (with no arguments) that
    is later reversed into proper URL.
    """
    url = reverse(url_name)
    active = context['request'].path == url
    return mark_safe(navbar_template(title, url, active=active,
                                     dropdown=dropdown))


@register.simple_tag(takes_context=True)
def navbar_element_permed(context, title, url_name, perms, dropdown=False):
    """
    Works like `navbar_element`, but also disables if user doesn't have
    permissions.

    `perms` can be a comma-separated string of permissions or a single
    permission.
    """
    url = reverse(url_name)
    active = context['request'].path == url

    # check permissions
    perms_ctx = context['perms']
    perms = perms.split(',')
    # True for every perm (from perms_ctx) that's granted to the user
    perms = map(lambda x: x in perms_ctx, perms)
    disabled = not all(perms)  # or: enabled = all(perms)

    return mark_safe(navbar_template(title, url, active=active,
                                     dropdown=dropdown))


@register.simple_tag(takes_context=True)
def navbar_element_url(context, title, url, dropdown=False):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a pre-made URL as an argument.
    """
    active = context['request'].path == url
    return mark_safe(navbar_template(title, url, active=active,
                                     dropdown=dropdown))
