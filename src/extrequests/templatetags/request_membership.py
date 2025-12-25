from datetime import date

from django import template

from src.workshops.models import Membership

register = template.Library()


@register.simple_tag
def membership_alert_type(membership: Membership) -> str:
    workshops_remaining = membership.workshops_without_admin_fee_remaining
    active = membership.active_on_date(date.today())
    if workshops_remaining <= 0 or not active:
        return "warning"
    else:
        return "info"


@register.simple_tag
def membership_active(membership: Membership) -> bool:
    return membership.active_on_date(date.today())
