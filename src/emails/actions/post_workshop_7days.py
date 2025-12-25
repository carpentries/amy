import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from src.emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from src.emails.actions.base_strategy import run_strategy
from src.emails.models import ScheduledEmail
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    POST_WORKSHOP_7DAYS_SIGNAL_NAME,
    Signal,
    post_workshop_7days_cancel_signal,
    post_workshop_7days_signal,
    post_workshop_7days_update_signal,
)
from src.emails.types import PostWorkshop7DaysContext, PostWorkshop7DaysKwargs, StrategyEnum
from src.emails.utils import (
    api_model_url,
    log_condition_elements,
    scalar_value_none,
    shift_date_and_apply_set_time,
)
from src.workshops.models import Event, Task

logger = logging.getLogger("amy")

WEEK_OFFSET = timedelta(days=7)


def post_workshop_7days_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running PostWorkshop7Days strategy for {event}")

    centrally_organised = (
        event.administrator
        and event.administrator.domain != "self-organized"
        and event.administrator.domain != "carpentries.org/community-lessons/"
    )
    self_organised = event.administrator and event.administrator.domain == "self-organized"
    not_cldt = event.administrator and event.administrator.domain != "carpentries.org/community-lessons/"
    end_date_plus_7days_in_future = event.end and (event.end + WEEK_OFFSET) >= timezone.now().date()
    active = not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
    carpentries_tag = event.tags.filter(name__in=["LC", "DC", "SWC", "Circuits"])
    at_least_1_host = Task.objects.filter(role__name="host", event=event).count() >= 1
    at_least_1_instructor = Task.objects.filter(role__name="instructor", event=event).count() >= 1

    log_condition_elements(
        centrally_organised=centrally_organised,
        self_organised=self_organised,
        not_cldt=not_cldt,
        end_date_in_future=end_date_plus_7days_in_future,
        active=active,
        carpentries_tag=carpentries_tag,
        at_least_1_host=at_least_1_host,
        at_least_1_instructor=at_least_1_instructor,
    )

    email_exists = (
        # UPDATE 2025-02-15 (#2760):
        #      We're allowing scheduling for centrally-organised
        #      and self-organised workshops.
        (centrally_organised or self_organised)
        and not_cldt
        # UPDATE 2025-05-06 (#2792):
        #      Allow editing the event during 7 days after the workshop end date
        #      instead of cancelling it.
        and end_date_plus_7days_in_future
        and active
        and carpentries_tag
        and at_least_1_host
        and at_least_1_instructor
    )
    logger.debug(f"{email_exists=}")

    ct = ContentType.objects.get_for_model(event)
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=POST_WORKSHOP_7DAYS_SIGNAL_NAME,
    ).exists()
    logger.debug(f"{has_email_scheduled=}")

    if not has_email_scheduled and email_exists:
        result = StrategyEnum.CREATE
    elif has_email_scheduled and not email_exists:
        result = StrategyEnum.CANCEL
    elif has_email_scheduled and email_exists:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"PostWorkshop7Days strategy {result=}")
    return result


def run_post_workshop_7days_strategy(strategy: StrategyEnum, request: HttpRequest, event: Event, **kwargs: Any) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: post_workshop_7days_signal,
        StrategyEnum.UPDATE: post_workshop_7days_update_signal,
        StrategyEnum.CANCEL: post_workshop_7days_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=event,
        event=event,
        event_end_date=event.end,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[PostWorkshop7DaysKwargs]) -> datetime:
    # Should run 7 days after the event end date.
    event_end_date = kwargs["event_end_date"]
    week_after_event = shift_date_and_apply_set_time(
        event_end_date, offset=WEEK_OFFSET, time_=time(12, 0, 0, tzinfo=UTC)
    )
    return week_after_event


def get_context(**kwargs: Unpack[PostWorkshop7DaysKwargs]) -> PostWorkshop7DaysContext:
    event = kwargs["event"]
    hosts = [task.person for task in Task.objects.filter(role__name="host", event=event)]
    instructors = [task.person for task in Task.objects.filter(role__name="instructor", event=event)]
    helpers = [task.person for task in Task.objects.filter(role__name="helper", event=event)]
    return {
        "assignee": event.assigned_to if event.assigned_to else None,
        "event": event,
        "hosts": hosts,
        "instructors": instructors,
        "helpers": helpers,
    }


def get_context_json(context: PostWorkshop7DaysContext) -> ContextModel:
    event = context["event"]
    return ContextModel(
        {
            "assignee": (
                api_model_url("person", context["assignee"].pk) if context["assignee"] else scalar_value_none()
            ),
            "event": api_model_url("event", event.pk),
            "hosts": [api_model_url("person", person.pk) for person in context["hosts"]],
            "instructors": [api_model_url("person", person.pk) for person in context["instructors"]],
            "helpers": [api_model_url("person", person.pk) for person in context["helpers"]],
        },
    )


def get_generic_relation_object(context: PostWorkshop7DaysContext, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> Event:
    return context["event"]


def get_recipients(context: PostWorkshop7DaysContext, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> list[str]:
    return [host.email for host in context["hosts"] if host.email] + [
        instructor.email for instructor in context["instructors"] if instructor.email
    ]


def get_recipients_context_json(
    context: PostWorkshop7DaysContext, **kwargs: Unpack[PostWorkshop7DaysKwargs]
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", host.pk),
                property="email",
            )
            for host in context["hosts"]
        ]
        + [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", instructor.pk),
                property="email",
            )
            for instructor in context["instructors"]
        ],
    )


class PostWorkshop7DaysReceiver(BaseAction):
    signal = post_workshop_7days_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> PostWorkshop7DaysContext:
        return get_context(**kwargs)

    def get_context_json(self, context: PostWorkshop7DaysContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class PostWorkshop7DaysUpdateReceiver(BaseActionUpdate):
    signal = post_workshop_7days_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> PostWorkshop7DaysContext:
        return get_context(**kwargs)

    def get_context_json(self, context: PostWorkshop7DaysContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class PostWorkshop7DaysCancelReceiver(BaseActionCancel):
    signal = post_workshop_7days_signal.signal_name

    def get_context(self, **kwargs: Unpack[PostWorkshop7DaysKwargs]) -> PostWorkshop7DaysContext:
        return get_context(**kwargs)

    def get_context_json(self, context: PostWorkshop7DaysContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: PostWorkshop7DaysContext,
        **kwargs: Unpack[PostWorkshop7DaysKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


post_workshop_7days_receiver = PostWorkshop7DaysReceiver()
post_workshop_7days_signal.connect(post_workshop_7days_receiver)

post_workshop_7days_update_receiver = PostWorkshop7DaysUpdateReceiver()
post_workshop_7days_update_signal.connect(post_workshop_7days_update_receiver)

post_workshop_7days_cancel_receiver = PostWorkshop7DaysCancelReceiver()
post_workshop_7days_cancel_signal.connect(post_workshop_7days_cancel_receiver)
