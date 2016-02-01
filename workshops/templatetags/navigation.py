from django import template
from django.core.urlresolvers import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


def navbar_template(title, url, active=False, disabled=False):
    """
    Compose an HTML anchor <a href='' /> inside a list item <li>.

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
        screen_reader = mark_safe('<span class="sr-only">(active)</span>')

    if classes:
        classes = ' '.join(classes)
        template = ('<li class="{classes}"><a href="{url}">{title} '
                    '{screen_reader}</a></li>')
        # return template.format(classes=classes, url=url, title=title,
        #                        screen_reader=screen_reader)
        return format_html(template, classes=classes, url=url,
                           title=title, screen_reader=screen_reader)
    else:
        template = ('<li><a href="{url}">{title}</a></li>')
        # return template.format(url=url, title=title)
        return format_html(template, url=url, title=title)


@register.simple_tag(takes_context=True)
def navbar_element(context, title, url_name):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a URL name (with no arguments) that
    is later reversed into proper URL.
    """
    url = reverse(url_name)
    active = context['request'].path == url
    return mark_safe(navbar_template(title, url, active=active))


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

    # check permissions
    perms_ctx = context['perms']
    perms = perms.split(',')
    # True for every perm (from perms_ctx) that's granted to the user
    perms = map(lambda x: x in perms_ctx, perms)
    disabled = not all(perms)  # or: enabled = all(perms)

    return mark_safe(navbar_template(title, url, active=active,
                                     disabled=disabled))


@register.simple_tag(takes_context=True)
def navbar_element_url(context, title, url):
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a pre-made URL as an argument.
    """
    active = context['request'].path == url
    return mark_safe(navbar_template(title, url, active=active))
