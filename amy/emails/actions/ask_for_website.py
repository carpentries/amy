from datetime import datetime
import logging

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone
from typing_extensions import Unpack

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.models import ScheduledEmail
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import (
    ASK_FOR_WEBSITE_SIGNAL_NAME,
    Signal,
    ask_for_website_cancel_signal,
    ask_for_website_signal,
    ask_for_website_update_signal,
)
from emails.types import AskForWebsiteContext, AskForWebsiteKwargs, StrategyEnum
from emails.utils import (
    api_model_url,
    log_condition_elements,
    one_month_before,
    scalar_value_none,
)
from workshops.models import Event, TagQuerySet, Task

logger = logging.getLogger("amy")


def ask_for_website_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running AskForWebsite strategy for {event}")

    start_date_in_future = event.start and event.start >= timezone.now().date()
    active = not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
    has_administrator = event.administrator
    no_url = not event.url
    has_instructors = Task.objects.filter(event=event, role__name="instructor").count() >= 1
    carpentries_tags = event.tags.filter(name__in=TagQuerySet.CARPENTRIES_TAG_NAMES).exclude(
        name__in=TagQuerySet.NON_CARPENTRIES_TAG_NAMES
    )

    log_condition_elements(
        start_date_in_future=start_date_in_future,
        active=active,
        has_administrator=has_administrator,
        no_url=no_url,
        has_instructors=has_instructors,
        carpentries_tags=carpentries_tags,
    )

    email_should_exist = (
        start_date_in_future and active and has_administrator and no_url and has_instructors and carpentries_tags
    )
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=ASK_FOR_WEBSITE_SIGNAL_NAME,
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

    logger.debug(f"AskForWebsite strategy {result=}")
    return result


def run_ask_for_website_strategy(strategy: StrategyEnum, request: HttpRequest, event: Event, **kwargs) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: ask_for_website_signal,
        StrategyEnum.UPDATE: ask_for_website_update_signal,
        StrategyEnum.CANCEL: ask_for_website_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=event,
        event=event,
        event_start_date=event.start,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[AskForWebsiteKwargs]) -> datetime:
    event_start_date = kwargs["event_start_date"]
    return one_month_before(event_start_date)


def get_context(
    **kwargs: Unpack[AskForWebsiteKwargs],
) -> AskForWebsiteContext:
    event = kwargs["event"]
    instructors = [task.person for task in Task.objects.filter(event=event, role__name="instructor")]
    return {
        "assignee": event.assigned_to if event.assigned_to else None,
        "event": event,
        "instructors": instructors,
    }


def get_context_json(context: AskForWebsiteContext) -> ContextModel:
    event = context["event"]
    return ContextModel(
        {
            "assignee": (
                api_model_url("person", context["assignee"].pk) if context["assignee"] else scalar_value_none()
            ),
            "event": api_model_url("event", event.pk),
            "instructors": [api_model_url("person", person.pk) for person in context["instructors"]],
        },
    )


def get_generic_relation_object(
    context: AskForWebsiteContext,
    **kwargs: Unpack[AskForWebsiteKwargs],
) -> Event:
    return context["event"]


def get_recipients(
    context: AskForWebsiteContext,
    **kwargs: Unpack[AskForWebsiteKwargs],
) -> list[str]:
    instructors = context["instructors"]
    return [instructor.email for instructor in instructors if instructor.email]


def get_recipients_context_json(
    context: AskForWebsiteContext,
    **kwargs: Unpack[AskForWebsiteKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            {
                "api_uri": api_model_url("person", instructor.pk),
                "property": "email",
            }
            for instructor in context["instructors"]
        ],  # type: ignore
    )


class AskForWebsiteReceiver(BaseAction):
    signal = ask_for_website_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[AskForWebsiteKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[AskForWebsiteKwargs]) -> AskForWebsiteContext:
        return get_context(**kwargs)

    def get_context_json(self, context: AskForWebsiteContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class AskForWebsiteUpdateReceiver(BaseActionUpdate):
    signal = ask_for_website_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[AskForWebsiteKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[AskForWebsiteKwargs]) -> AskForWebsiteContext:
        return get_context(**kwargs)

    def get_context_json(self, context: AskForWebsiteContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class AskForWebsiteCancelReceiver(BaseActionCancel):
    signal = ask_for_website_cancel_signal.signal_name

    def get_context(self, **kwargs: Unpack[AskForWebsiteKwargs]) -> AskForWebsiteContext:
        return get_context(**kwargs)

    def get_context_json(self, context: AskForWebsiteContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: AskForWebsiteContext,
        **kwargs: Unpack[AskForWebsiteKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

ask_for_website_receiver = AskForWebsiteReceiver()
ask_for_website_signal.connect(ask_for_website_receiver)


ask_for_website_update_receiver = AskForWebsiteUpdateReceiver()
ask_for_website_update_signal.connect(ask_for_website_update_receiver)


ask_for_website_cancel_receiver = AskForWebsiteCancelReceiver()
ask_for_website_cancel_signal.connect(ask_for_website_cancel_receiver)
