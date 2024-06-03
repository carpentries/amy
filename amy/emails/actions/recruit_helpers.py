from datetime import datetime, timedelta
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
    RECRUIT_HELPERS_SIGNAL_NAME,
    Signal,
    recruit_helpers_cancel_signal,
    recruit_helpers_signal,
    recruit_helpers_update_signal,
)
from emails.types import RecruitHelpersContext, RecruitHelpersKwargs, StrategyEnum
from emails.utils import (
    api_model_url,
    log_condition_elements,
    scalar_value_none,
    shift_date_and_apply_current_utc_time,
)
from workshops.models import Event, Task

logger = logging.getLogger("amy")


def recruit_helpers_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running RecruitHelpers strategy for {event}")

    not_self_organised = (
        event.administrator and event.administrator.domain != "self-organized"
    )
    start_date_in_at_least_14days = event.start and event.start >= (
        timezone.now().date() + timedelta(days=14)
    )
    active = not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
    at_least_1_host = Task.objects.filter(role__name="host", event=event).count() >= 1
    at_least_1_instructor = (
        Task.objects.filter(role__name="instructor", event=event).count() >= 1
    )
    no_helpers = Task.objects.filter(role__name="helper", event=event).count() == 0

    log_condition_elements(
        not_self_organised=not_self_organised,
        start_date_in_at_least_14days=start_date_in_at_least_14days,
        active=active,
        at_least_1_host=at_least_1_host,
        at_least_1_instructor=at_least_1_instructor,
        no_helpers=no_helpers,
    )

    email_should_exist = (
        not_self_organised
        and start_date_in_at_least_14days
        and active
        and at_least_1_host
        and at_least_1_instructor
        and no_helpers
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=RECRUIT_HELPERS_SIGNAL_NAME,
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

    logger.debug(f"RecruitHelpers strategy {result = }")
    return result


def run_recruit_helpers_strategy(
    strategy: StrategyEnum, request: HttpRequest, event: Event
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: recruit_helpers_signal,
        StrategyEnum.UPDATE: recruit_helpers_update_signal,
        StrategyEnum.CANCEL: recruit_helpers_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=event,
        event=event,
        event_start_date=event.start,
    )


def get_scheduled_at(**kwargs: Unpack[RecruitHelpersKwargs]) -> datetime:
    # Should run 21 days before the event start date.
    event_start_date = kwargs["event_start_date"]
    return shift_date_and_apply_current_utc_time(
        event_start_date, offset=-timedelta(days=21)
    )


def get_context(**kwargs: Unpack[RecruitHelpersKwargs]) -> RecruitHelpersContext:
    event = kwargs["event"]
    instructors = [
        task.person
        for task in Task.objects.filter(role__name="instructor", event=event)
    ]
    hosts = [
        task.person for task in Task.objects.filter(role__name="host", event=event)
    ]
    return {
        "assignee": event.assigned_to if event.assigned_to else None,
        "event": event,
        "instructors": instructors,
        "hosts": hosts,
    }


def get_context_json(context: RecruitHelpersContext) -> ContextModel:
    event = context["event"]
    return ContextModel(
        {
            "assignee": (
                api_model_url("person", context["assignee"].pk)
                if context["assignee"]
                else scalar_value_none()
            ),
            "event": api_model_url("event", event.pk),
            "instructors": [
                api_model_url("person", person.pk) for person in context["instructors"]
            ],
            "hosts": [
                api_model_url("person", person.pk) for person in context["hosts"]
            ],
        },
    )


def get_generic_relation_object(
    context: RecruitHelpersContext, **kwargs: Unpack[RecruitHelpersKwargs]
) -> Event:
    return context["event"]


def get_recipients(
    context: RecruitHelpersContext, **kwargs: Unpack[RecruitHelpersKwargs]
) -> list[str]:
    return [
        instructor.email for instructor in context["instructors"] if instructor.email
    ] + [host.email for host in context["hosts"] if host.email]


def get_recipients_context_json(
    context: RecruitHelpersContext, **kwargs: Unpack[RecruitHelpersKwargs]
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            {
                "api_uri": api_model_url("person", instructor.pk),
                "property": "email",
            }
            for instructor in context["instructors"]
        ]
        + [
            {
                "api_uri": api_model_url("person", host.pk),
                "property": "email",
            }
            for host in context["hosts"]
        ],  # type: ignore
    )


class RecruitHelpersReceiver(BaseAction):
    signal = recruit_helpers_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[RecruitHelpersKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[RecruitHelpersKwargs]
    ) -> RecruitHelpersContext:
        return get_context(**kwargs)

    def get_context_json(self, context: RecruitHelpersContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class RecruitHelpersUpdateReceiver(BaseActionUpdate):
    signal = recruit_helpers_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[RecruitHelpersKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[RecruitHelpersKwargs]
    ) -> RecruitHelpersContext:
        return get_context(**kwargs)

    def get_context_json(self, context: RecruitHelpersContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class RecruitHelpersCancelReceiver(BaseActionCancel):
    signal = recruit_helpers_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[RecruitHelpersKwargs]
    ) -> RecruitHelpersContext:
        return get_context(**kwargs)

    def get_context_json(self, context: RecruitHelpersContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: RecruitHelpersContext,
        **kwargs: Unpack[RecruitHelpersKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


recruit_helpers_receiver = RecruitHelpersReceiver()
recruit_helpers_signal.connect(recruit_helpers_receiver)

recruit_helpers_update_receiver = RecruitHelpersUpdateReceiver()
recruit_helpers_update_signal.connect(recruit_helpers_update_receiver)

recruit_helpers_cancel_receiver = RecruitHelpersCancelReceiver()
recruit_helpers_cancel_signal.connect(recruit_helpers_cancel_receiver)
