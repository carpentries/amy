from datetime import datetime
import logging
from typing import Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import (
    NEW_SELF_ORGANISED_WORKSHOP_SIGNAL_NAME,
    Signal,
    new_self_organised_workshop_cancel_signal,
    new_self_organised_workshop_signal,
    new_self_organised_workshop_update_signal,
)
from emails.types import (
    NewSelfOrganisedWorkshopContext,
    NewSelfOrganisedWorkshopKwargs,
    StrategyEnum,
)
from emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
    scalar_value_url,
)
from extrequests.models import SelfOrganisedSubmission
from workshops.fields import TAG_SEPARATOR
from workshops.models import Event

logger = logging.getLogger("amy")


def new_self_organised_workshop_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running NewSelfOrganisedWorkshop strategy for {event}")

    self_organised = (
        event.administrator and event.administrator.domain == "self-organized"
    )
    start_date_in_future = event.start and event.start >= timezone.now().date()
    active = not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
    submission = SelfOrganisedSubmission.objects.filter(event=event).exists()

    log_condition_elements(
        self_organised=self_organised,
        start_date_in_future=start_date_in_future,
        active=active,
        submission=submission,
    )

    email_should_exist = (
        self_organised and start_date_in_future and active and submission
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=NEW_SELF_ORGANISED_WORKSHOP_SIGNAL_NAME,
        state=ScheduledEmailStatus.SCHEDULED,
    ).exists()
    logger.debug(f"{has_email_scheduled=}")

    if not has_email_scheduled and email_should_exist:
        result = StrategyEnum.CREATE
    elif has_email_scheduled and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif has_email_scheduled and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"NewSelfOrganisedWorkshop strategy {result = }")
    return result


def run_new_self_organised_workshop_strategy(
    strategy: StrategyEnum,
    request: HttpRequest,
    event: Event,
    self_organised_submission: SelfOrganisedSubmission,
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: new_self_organised_workshop_signal,
        StrategyEnum.UPDATE: new_self_organised_workshop_update_signal,
        StrategyEnum.CANCEL: new_self_organised_workshop_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=event,
        event=event,
        self_organised_submission=self_organised_submission,
    )


def get_scheduled_at(**kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
) -> NewSelfOrganisedWorkshopContext:
    event = kwargs["event"]
    self_organised_submission = kwargs["self_organised_submission"]
    return {
        # Both self-organised submission and event can have assignees, but we prefer
        # the one from submission.
        "assignee": self_organised_submission.assigned_to or event.assigned_to or None,
        "event": event,
        "self_organised_submission": self_organised_submission,
    }


def get_context_json(context: NewSelfOrganisedWorkshopContext) -> ContextModel:
    return ContextModel(
        {
            "assignee": (
                api_model_url("person", context["assignee"].pk)
                if context["assignee"]
                else scalar_value_none()
            ),
            "event": api_model_url("event", context["event"].pk),
            "self_organised_submission": api_model_url(
                "selforganisedsubmission", context["self_organised_submission"].pk
            ),
        },
    )


def get_generic_relation_object(
    context: NewSelfOrganisedWorkshopContext,
    **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
) -> Event:
    return context["event"]


def get_recipients(
    context: NewSelfOrganisedWorkshopContext,
    **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
) -> list[str]:
    self_organised_submission = context["self_organised_submission"]
    return [
        self_organised_submission.email
    ] + self_organised_submission.additional_contact.split(TAG_SEPARATOR)


def get_recipients_context_json(
    context: NewSelfOrganisedWorkshopContext,
    **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
) -> ToHeaderModel:
    self_organised_submission = context["self_organised_submission"]
    return ToHeaderModel(
        [
            {
                "api_uri": api_model_url(
                    "selforganisedsubmission", self_organised_submission.pk
                ),
                "property": "email",
            }
        ]
        + [
            # Note: this won't update automatically
            {"value_uri": scalar_value_url("str", email)}
            for email in self_organised_submission.additional_contact.split(
                TAG_SEPARATOR
            )
        ],  # type: ignore
    )


class NewSelfOrganisedWorkshopReceiver(BaseAction):
    signal = new_self_organised_workshop_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]
    ) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]
    ) -> NewSelfOrganisedWorkshopContext:
        return get_context(**kwargs)

    def get_context_json(
        self, context: NewSelfOrganisedWorkshopContext
    ) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class NewSelfOrganisedWorkshopUpdateReceiver(BaseActionUpdate):
    signal = new_self_organised_workshop_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]
    ) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]
    ) -> NewSelfOrganisedWorkshopContext:
        return get_context(**kwargs)

    def get_context_json(
        self, context: NewSelfOrganisedWorkshopContext
    ) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class NewSelfOrganisedWorkshopCancelReceiver(BaseActionCancel):
    signal = new_self_organised_workshop_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs]
    ) -> NewSelfOrganisedWorkshopContext:
        return get_context(**kwargs)

    def get_context_json(
        self, context: NewSelfOrganisedWorkshopContext
    ) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: NewSelfOrganisedWorkshopContext,
        **kwargs: Unpack[NewSelfOrganisedWorkshopKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


new_self_organised_workshop_receiver = NewSelfOrganisedWorkshopReceiver()
new_self_organised_workshop_signal.connect(new_self_organised_workshop_receiver)

new_self_organised_workshop_update_receiver = NewSelfOrganisedWorkshopUpdateReceiver()
new_self_organised_workshop_update_signal.connect(
    new_self_organised_workshop_update_receiver
)

new_self_organised_workshop_cancel_receiver = NewSelfOrganisedWorkshopCancelReceiver()
new_self_organised_workshop_cancel_signal.connect(
    new_self_organised_workshop_cancel_receiver
)
