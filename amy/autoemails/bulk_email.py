from __future__ import annotations

import logging
from typing import Any, Type

from django.conf import settings
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from autoemails.actions import BaseAction
from autoemails.base_views import ActionManageMixin
from autoemails.models import Trigger

logger = logging.getLogger("amy")


def send_bulk_email(
    request: HttpRequest,
    action_class: Type[BaseAction],
    triggers: QuerySet[Trigger],
    emails: list[str],
    additional_context_objects: dict,
    object_: Any,
):
    emails_to_send = [
        emails[i : i + settings.BULK_EMAIL_LIMIT]  # noqa
        for i in range(0, len(emails), settings.BULK_EMAIL_LIMIT)
    ]
    for emails in emails_to_send:
        jobs, rqjobs = ActionManageMixin.add(
            action_class=action_class,
            logger=logger,
            triggers=triggers,
            context_objects=dict(
                person_emails=emails,
                **additional_context_objects,
            ),
            object_=object_,
        )
        if triggers and jobs:
            ActionManageMixin.bulk_schedule_message(
                request=request,
                num_emails=len(emails),
                trigger=triggers[0],
                job=jobs[0],
            )
