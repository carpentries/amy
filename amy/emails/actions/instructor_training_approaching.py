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
    INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
    Signal,
    instructor_training_approaching_cancel_signal,
    instructor_training_approaching_signal,
    instructor_training_approaching_update_signal,
)
from emails.types import (
    InstructorTrainingApproachingContext,
    InstructorTrainingApproachingKwargs,
    StrategyEnum,
)
from emails.utils import api_model_url, log_condition_elements, one_month_before
from workshops.models import Event, Task

logger = logging.getLogger("amy")


def instructor_training_approaching_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running InstructorTrainingApproaching strategy for {event}")

    has_TTT = event.tags.filter(name="TTT").exists()
    has_at_least_2_instructors = Task.objects.filter(event=event, role__name="instructor").count() >= 2
    start_date_in_future = event.start and event.start >= timezone.now().date()

    log_condition_elements(
        has_TTT=has_TTT,
        has_at_least_2_instructors=has_at_least_2_instructors,
        start_date_in_future=start_date_in_future,
    )

    email_should_exist = has_TTT and has_at_least_2_instructors and start_date_in_future
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    email_exists = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
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

    logger.debug(f"InstructorTrainingApproaching strategy {result=}")
    return result


def run_instructor_training_approaching_strategy(
    strategy: StrategyEnum, request: HttpRequest, event: Event, **kwargs
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_training_approaching_signal,
        StrategyEnum.UPDATE: instructor_training_approaching_update_signal,
        StrategyEnum.CANCEL: instructor_training_approaching_cancel_signal,
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


def get_scheduled_at(**kwargs: Unpack[InstructorTrainingApproachingKwargs]) -> datetime:
    event_start_date = kwargs["event_start_date"]
    return one_month_before(event_start_date)


def get_context(
    **kwargs: Unpack[InstructorTrainingApproachingKwargs],
) -> InstructorTrainingApproachingContext:
    event = kwargs["event"]
    instructors = [task.person for task in Task.objects.filter(event=event, role__name="instructor")]
    return {
        "event": event,
        "instructors": instructors,
    }


def get_context_json(context: InstructorTrainingApproachingContext) -> ContextModel:
    return ContextModel(
        {
            "event": api_model_url("event", context["event"].pk),
            "instructors": [api_model_url("person", person.pk) for person in context["instructors"]],
        },
    )


def get_generic_relation_object(
    context: InstructorTrainingApproachingContext,
    **kwargs: Unpack[InstructorTrainingApproachingKwargs],
) -> Event:
    return context["event"]


def get_recipients(
    context: InstructorTrainingApproachingContext,
    **kwargs: Unpack[InstructorTrainingApproachingKwargs],
) -> list[str]:
    instructors = context["instructors"]
    return [instructor.email for instructor in instructors if instructor.email]


def get_recipients_context_json(
    context: InstructorTrainingApproachingContext,
    **kwargs: Unpack[InstructorTrainingApproachingKwargs],
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


class InstructorTrainingApproachingReceiver(BaseAction):
    signal = instructor_training_approaching_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> InstructorTrainingApproachingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTrainingApproachingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorTrainingApproachingUpdateReceiver(BaseActionUpdate):
    signal = instructor_training_approaching_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> InstructorTrainingApproachingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTrainingApproachingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorTrainingApproachingCancelReceiver(BaseActionCancel):
    signal = instructor_training_approaching_cancel_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> InstructorTrainingApproachingContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTrainingApproachingContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> Event:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

instructor_training_approaching_receiver = InstructorTrainingApproachingReceiver()
instructor_training_approaching_signal.connect(instructor_training_approaching_receiver)


instructor_training_approaching_update_receiver = InstructorTrainingApproachingUpdateReceiver()
instructor_training_approaching_update_signal.connect(instructor_training_approaching_update_receiver)


instructor_training_approaching_cancel_receiver = InstructorTrainingApproachingCancelReceiver()
instructor_training_approaching_cancel_signal.connect(instructor_training_approaching_cancel_receiver)
