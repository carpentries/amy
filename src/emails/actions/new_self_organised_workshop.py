import logging
from datetime import datetime, timedelta
from typing import Unpack

from django.utils import timezone

from src.emails.actions.base_action import BaseAction
from src.emails.schemas import (
    ContextModel,
    SinglePropertyLinkModel,
    SingleValueLinkModel,
    ToHeaderModel,
)
from src.emails.signals import new_self_organised_workshop_signal
from src.emails.types import NewSelfOrganisedWorkshopContext, NewSelfOrganisedWorkshopKwargs
from src.emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
    scalar_value_url,
)
from src.extrequests.models import SelfOrganisedSubmission
from src.workshops.fields import TAG_SEPARATOR
from src.workshops.models import Event

logger = logging.getLogger("amy")


def new_self_organised_workshop_check(event: Event) -> bool:
    logger.info(f"Checking NewSelfOrganisedWorkshop conditions for {event}")

    self_organised = event.administrator and event.administrator.domain == "self-organized"
    start_date_in_future = event.start and event.start >= timezone.now().date()
    active = not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
    submission = SelfOrganisedSubmission.objects.filter(event=event).exists()

    log_condition_elements(
        self_organised=self_organised,
        start_date_in_future=start_date_in_future,
        active=active,
        submission=submission,
    )

    email_should_exist = bool(self_organised and start_date_in_future and active and submission)
    logger.debug(f"{email_should_exist=}")
    logger.debug(f"NewSelfOrganisedWorkshop condition check: {email_should_exist}")
    return email_should_exist


class NewSelfOrganisedWorkshopReceiver(BaseAction):
    signal = new_self_organised_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]) -> datetime:
        return immediate_action()

    def get_context(self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]) -> NewSelfOrganisedWorkshopContext:
        event = kwargs["event"]
        self_organised_submission = kwargs["self_organised_submission"]
        return {
            # Both self-organised submission and event can have assignees, but we prefer
            # the one from submission.
            "assignee": self_organised_submission.assigned_to or event.assigned_to or None,
            "workshop_host": event.host,
            "event": event,
            "short_notice": bool(event.start and event.start <= (timezone.now().date() + timedelta(days=10))),
            "self_organised_submission": self_organised_submission,
        }

    def get_context_json(self, context: NewSelfOrganisedWorkshopContext) -> ContextModel:
        return ContextModel(
            {
                "assignee": (
                    api_model_url("person", context["assignee"].pk) if context["assignee"] else scalar_value_none()
                ),
                "workshop_host": api_model_url("organization", context["workshop_host"].pk),
                "event": api_model_url("event", context["event"].pk),
                "short_notice": scalar_value_url("bool", str(context["short_notice"])),
                "self_organised_submission": api_model_url(
                    "selforganisedsubmission", context["self_organised_submission"].pk
                ),
            },
        )

    def get_generic_relation_object(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> Event:
        return context["event"]

    def get_recipients(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> list[str]:
        self_organised_submission = context["self_organised_submission"]
        return list(
            filter(
                bool,
                [self_organised_submission.email] + self_organised_submission.additional_contact.split(TAG_SEPARATOR),
            )
        )

    def get_recipients_context_json(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> ToHeaderModel:
        self_organised_submission = context["self_organised_submission"]
        return ToHeaderModel(
            (
                [
                    SinglePropertyLinkModel(
                        api_uri=api_model_url("selforganisedsubmission", self_organised_submission.pk),
                        property="email",
                    )
                ]
                if self_organised_submission.email
                else []
            )
            + [
                # Note: this won't update automatically
                SingleValueLinkModel(
                    value_uri=scalar_value_url("str", email),
                )
                for email in self_organised_submission.additional_contact.split(TAG_SEPARATOR)
                if email
            ],
        )


new_self_organised_workshop_receiver = NewSelfOrganisedWorkshopReceiver()
new_self_organised_workshop_signal.connect(new_self_organised_workshop_receiver)
