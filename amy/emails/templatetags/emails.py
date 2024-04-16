from django import template
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, QuerySet

from emails.models import (
    ScheduledEmail,
    ScheduledEmailStatus,
    ScheduledEmailStatusActions,
)

register = template.Library()


@register.simple_tag
def allowed_actions_for_status(status: ScheduledEmailStatus) -> list[str]:
    return [
        key
        for key, statuses in ScheduledEmailStatusActions.items()
        if status in statuses
    ]


@register.simple_tag
def get_related_scheduled_emails(obj: Model) -> QuerySet[ScheduledEmail]:
    content_type = ContentType.objects.get_for_model(obj.__class__)
    return ScheduledEmail.objects.filter(
        generic_relation_content_type=content_type,
        generic_relation_pk=obj.pk,
    ).order_by("-created_at")
