from datetime import datetime, timedelta
import logging
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME,
    Signal,
    host_instructors_introduction_cancel_signal,
    host_instructors_introduction_signal,
    host_instructors_introduction_update_signal,
)
from emails.types import (
    HostInstructorsIntroductionContext,
    HostInstructorsIntroductionKwargs,
    StrategyEnum,
)
from emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
)
from recruitment.models import InstructorRecruitment
from workshops.models import Event, TagQuerySet, Task

logger = logging.getLogger("amy")


def host_instructors_introduction_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running HostInstructorsIntroduction strategy for {event}")

    not_self_organised = event.administrator and event.administrator.domain != "self-organized"
    no_open_recruitment = not InstructorRecruitment.objects.filter(status="o", event=event).exists()
    start_date_in_at_least_7days = event.start and event.start >= (timezone.now().date() + timedelta(days=7))
    active = not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
    host = Task.objects.filter(role__name="host", event=event).first()
    at_least_2_instructors = Task.objects.filter(role__name="instructor", event=event).count() >= 2
    carpentries_tags = event.tags.filter(name__in=TagQuerySet.CARPENTRIES_TAG_NAMES).exclude(
        name__in=TagQuerySet.NON_CARPENTRIES_TAG_NAMES
    )

    log_condition_elements(
        not_self_organised=not_self_organised,
        no_open_recruitment=no_open_recruitment,
        start_date_in_at_least_7days=start_date_in_at_least_7days,
        active=active,
        host=host,
        at_least_2_instructors=at_least_2_instructors,
        carpentries_tags=carpentries_tags,
    )

    email_should_exist = (
        not_self_organised
        and start_date_in_at_least_7days
        and active
        and host
        and at_least_2_instructors
        and no_open_recruitment
        and carpentries_tags
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(event)
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME,
    ).exists()
    logger.debug(f"{email_exists=}")

    if not email_exists and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_exists and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_exists and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"HostInstructorsIntroduction strategy {result=}")
    return result


def run_host_instructors_introduction_strategy(
    strategy: StrategyEnum, request: HttpRequest, event: Event, **kwargs: Any
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: host_instructors_introduction_signal,
        StrategyEnum.UPDATE: host_instructors_introduction_update_signal,
        StrategyEnum.CANCEL: host_instructors_introduction_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=event,
        event=event,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[HostInstructorsIntroductionKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[HostInstructorsIntroductionKwargs],
) -> HostInstructorsIntroductionContext:
    event = kwargs["event"]

    try:
        host = Task.objects.filter(role__name="host", event=event)[0]
    except IndexError:
        host = None

    instructors = [task.person for task in Task.objects.filter(role__name="instructor", event=event)]
    return {
        "assignee": event.assigned_to if event.assigned_to else None,
        "event": event,
        "workshop_host": event.host if event.host else None,
        "host": host.person if host else None,
        "instructors": instructors,
    }


def get_context_json(context: HostInstructorsIntroductionContext) -> ContextModel:
    event = context["event"]
    return ContextModel(
        {
            "assignee": (
                api_model_url("person", context["assignee"].pk) if context["assignee"] else scalar_value_none()
            ),
            "event": api_model_url("event", event.pk),
            "workshop_host": (
                api_model_url("organization", context["workshop_host"].pk)
                if context["workshop_host"]
                else scalar_value_none()
            ),
            "host": (api_model_url("person", context["host"].pk) if context["host"] else scalar_value_none()),
            "instructors": [api_model_url("person", person.pk) for person in context["instructors"]],
        },
    )


def get_generic_relation_object(
    context: HostInstructorsIntroductionContext,
    **kwargs: Unpack[HostInstructorsIntroductionKwargs],
) -> Event:
    return context["event"]


def get_recipients(
    context: HostInstructorsIntroductionContext,
    **kwargs: Unpack[HostInstructorsIntroductionKwargs],
) -> list[str]:
    host = context["host"]
    host_part = [host.email] if host and host.email else []
    instructors_part = [instructor.email for instructor in context["instructors"] if instructor.email]
    return host_part + instructors_part


def get_recipients_context_json(
    context: HostInstructorsIntroductionContext,
    **kwargs: Unpack[HostInstructorsIntroductionKwargs],
) -> ToHeaderModel:
    host = context["host"]
    return ToHeaderModel(
        (
            [
                SinglePropertyLinkModel(
                    api_uri=api_model_url("person", host.pk),
                    property="email",
                )
            ]
            if host and host.email
            else []
        )
        + [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", instructor.pk),
                property="email",
            )
            for instructor in context["instructors"]
        ]
    )


class HostInstructorsIntroductionReceiver(BaseAction):
    signal = host_instructors_introduction_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[HostInstructorsIntroductionKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[HostInstructorsIntroductionKwargs]) -> HostInstructorsIntroductionContext:
        return get_context(**kwargs)

    def get_context_json(self, context: HostInstructorsIntroductionContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class HostInstructorsIntroductionUpdateReceiver(BaseActionUpdate):
    signal = host_instructors_introduction_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[HostInstructorsIntroductionKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[HostInstructorsIntroductionKwargs]) -> HostInstructorsIntroductionContext:
        return get_context(**kwargs)

    def get_context_json(self, context: HostInstructorsIntroductionContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class HostInstructorsIntroductionCancelReceiver(BaseActionCancel):
    signal = host_instructors_introduction_signal.signal_name

    def get_context(self, **kwargs: Unpack[HostInstructorsIntroductionKwargs]) -> HostInstructorsIntroductionContext:
        return get_context(**kwargs)

    def get_context_json(self, context: HostInstructorsIntroductionContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: HostInstructorsIntroductionContext,
        **kwargs: Unpack[HostInstructorsIntroductionKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


host_instructors_introduction_receiver = HostInstructorsIntroductionReceiver()
host_instructors_introduction_signal.connect(host_instructors_introduction_receiver)

host_instructors_introduction_update_receiver = HostInstructorsIntroductionUpdateReceiver()
host_instructors_introduction_update_signal.connect(host_instructors_introduction_update_receiver)

host_instructors_introduction_cancel_receiver = HostInstructorsIntroductionCancelReceiver()
host_instructors_introduction_cancel_signal.connect(host_instructors_introduction_cancel_receiver)
