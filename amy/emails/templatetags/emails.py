from django import template

from emails.models import ScheduledEmailStatus, ScheduledEmailStatusActions

register = template.Library()


@register.simple_tag
def allowed_actions_for_status(status: ScheduledEmailStatus) -> list[str]:
    return [
        key
        for key, statuses in ScheduledEmailStatusActions.items()
        if status in statuses
    ]
