from datetime import date

from django import template
from django.utils.safestring import mark_safe

from workshops.models import Membership

register = template.Library()


@register.simple_tag
def membership_description(membership: Membership):
    workshops_remaining = membership.workshops_without_admin_fee_remaining
    active = membership.active_on_date(date.today())
    if workshops_remaining <= 0 or not active:
        alert_type = "warning"
    else:
        alert_type = "info"
    info = (
        f'<div class="alert alert-{alert_type}">'
        "Related membership: "
        f'<a href="{membership.get_absolute_url()}">{membership}</a>.'
        "<br>"
        f"This membership has <strong>{workshops_remaining}</strong> "
        f'workshop{"s" if workshops_remaining !=1 else ""} remaining.'
    )
    if not active:
        info += "<br>This membership is <strong>not currently active</strong>."
    info += "</div>"

    return mark_safe(info)
