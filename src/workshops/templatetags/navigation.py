from typing import Any

from django import template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


def navbar_template(
    title: str, url: str, active: bool = False, disabled: bool = False, dropdown: bool = False, deprecated: bool = False
) -> str:
    """Compose Bootstrap v4 <li> element for top navigation bar.

    List item can be added one or more class attributes:
    * active: to highlight currently visited tab
    * disabled: to disable access, for example for users without specific
      permissions.
    * dropdown: change styling a little bit to work with dropdowns in
      Bootstrap4
    * deprecated: add a deprecated badge to indicate old features
    """
    classes: list[str] = []
    screen_reader = ""
    badge = ""

    if disabled:
        classes.append("disabled")

    if active:
        classes.append("active")
        screen_reader = mark_safe(' <span class="sr-only">(current)</span>')

    if deprecated:
        badge = mark_safe('<span class="badge badge-secondary">deprecated</span> ')

    classes_str = " ".join(classes)
    template = '<li class="nav-item {classes}"><a class="nav-link" href="{url}">{badge}{title}{screen_reader}</a></li>'
    if dropdown:
        template = '<a class="dropdown-item {classes}" href="{url}">{badge}{title}{screen_reader}</a>'
    return format_html(
        template,
        classes=classes_str,
        url=url,
        badge=badge,
        title=title,
        screen_reader=screen_reader,
    )


@register.simple_tag(takes_context=True)
def navbar_element(
    context: dict[str, Any], title: str, url_name: str, dropdown: bool = False, deprecated: bool = False
) -> SafeString:
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a URL name (with no arguments) that
    is later reversed into proper URL.
    """
    url = reverse(url_name)
    active = context["request"].path == url
    return mark_safe(navbar_template(title, url, active=active, dropdown=dropdown, deprecated=deprecated))


@register.simple_tag(takes_context=True)
def navbar_element_permed(
    context: dict[str, Any], title: str, url_name: str, perms: str, dropdown: bool = False
) -> SafeString:
    """
    Works like `navbar_element`, but also disables if user doesn't have
    permissions.

    `perms` can be a comma-separated string of permissions or a single
    permission.
    """
    url = reverse(url_name)
    active = context["request"].path == url

    # check permissions
    perms_ctx = context["perms"]
    perms_list = perms.split(",")
    # True for every perm (from perms_ctx) that's granted to the user
    perms_active = map(lambda x: x in perms_ctx, perms_list)
    not all(perms_active)  # or: enabled = all(perms)

    return mark_safe(navbar_template(title, url, active=active, dropdown=dropdown))


@register.simple_tag(takes_context=True)
def navbar_element_url(context: dict[str, Any], title: str, url: str, dropdown: bool = False) -> SafeString:
    """
    Insert Bootstrap's `<li><a>...</a></li>` with specific classes and
    accessibility elements.  This tag takes a pre-made URL as an argument.
    """
    active = context["request"].path == url
    return mark_safe(navbar_template(title, url, active=active, dropdown=dropdown))
