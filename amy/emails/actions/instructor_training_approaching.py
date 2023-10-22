from datetime import datetime
import logging

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone
from typing_extensions import Unpack

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.models import ScheduledEmail
from emails.signals import (
    INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
    Signal,
    instructor_training_approaching_remove_signal,
    instructor_training_approaching_signal,
    instructor_training_approaching_update_signal,
)
from emails.types import (
    InstructorTrainingApproachingContext,
    InstructorTrainingApproachingKwargs,
    StrategyEnum,
)
from emails.utils import one_month_before
from workshops.models import Event, Task

logger = logging.getLogger("amy")


# TODO: move out to a common file
class EmailStrategyException(Exception):
    pass


def instructor_training_approaching_strategy(event: Event) -> StrategyEnum:
    logger.info(f"Running InstructorTrainingApproaching strategy for {event}")

    has_TTT = event.tags.filter(name="TTT").exists()
    has_at_least_2_instructors = (
        Task.objects.filter(event=event, role__name="instructor").count() >= 2
    )
    start_date_in_future = event.start and event.start >= timezone.now().date()
    logger.debug(f"{has_TTT=}, {has_at_least_2_instructors=}, {start_date_in_future=}")

    email_should_exist = has_TTT and has_at_least_2_instructors and start_date_in_future
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
        state="scheduled",
    ).exists()
    logger.debug(f"{has_email_scheduled=}")

    if not has_email_scheduled and email_should_exist:
        result = StrategyEnum.CREATE
    elif has_email_scheduled and not email_should_exist:
        result = StrategyEnum.REMOVE
    elif has_email_scheduled and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"InstructorTrainingApproaching strategy {result = }")
    return result


# TODO: turn into a generic function/class
def run_instructor_training_approaching_strategy(
    strategy: StrategyEnum, request: HttpRequest, event: Event
) -> None:
    mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_training_approaching_signal,
        StrategyEnum.UPDATE: instructor_training_approaching_update_signal,
        StrategyEnum.REMOVE: instructor_training_approaching_remove_signal,
        StrategyEnum.NOOP: None,
    }
    if strategy not in mapping:
        raise EmailStrategyException(f"Unknown strategy {strategy}")

    signal = mapping[strategy]

    if not signal:
        logger.debug(f"Strategy {strategy} for {event} is a no-op")
        return

    logger.debug(f"Sending signal for {event} as result of strategy {strategy}")
    signal.send(
        sender=event,
        request=request,
        event=event,
        event_start_date=event.start,
    )


class InstructorTrainingApproachingReceiver(BaseAction):
    signal = instructor_training_approaching_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> datetime:
        event_start_date = kwargs["event_start_date"]
        return one_month_before(event_start_date)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> InstructorTrainingApproachingContext:
        event = kwargs["event"]
        instructors = [
            task.person
            for task in Task.objects.filter(event=event, role__name="instructor")
        ]
        return {
            "event": event,
            "instructors": instructors,
        }

    def get_generic_relation_object(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> Event:
        return context["event"]

    def get_recipients(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> list[str]:
        instructors = context["instructors"]
        return [instructor.email for instructor in instructors if instructor.email]


class InstructorTrainingApproachingUpdateReceiver(BaseActionUpdate):
    signal = instructor_training_approaching_update_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> datetime:
        event_start_date = kwargs["event_start_date"]
        return one_month_before(event_start_date)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> InstructorTrainingApproachingContext:
        event = kwargs["event"]
        instructors = [
            task.person
            for task in Task.objects.filter(event=event, role__name="instructor")
        ]
        return {
            "event": event,
            "instructors": instructors,
        }

    def get_generic_relation_object(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> Event:
        return context["event"]

    def get_recipients(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> list[str]:
        instructors = context["instructors"]
        return [instructor.email for instructor in instructors if instructor.email]


class InstructorTrainingApproachingCancelReceiver(BaseActionCancel):
    signal = instructor_training_approaching_remove_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
    ) -> InstructorTrainingApproachingContext:
        event = kwargs["event"]
        instructors = [
            task.person
            for task in Task.objects.filter(event=event, role__name="instructor")
        ]
        return {
            "event": event,
            "instructors": instructors,
        }

    def get_generic_relation_object(
        self,
        context: InstructorTrainingApproachingContext,
        **kwargs: Unpack[InstructorTrainingApproachingKwargs],
    ) -> Event:
        return context["event"]


# -----------------------------------------------------------------------------
# Receivers

instructor_training_approaching_receiver = InstructorTrainingApproachingReceiver()
instructor_training_approaching_signal.connect(instructor_training_approaching_receiver)


instructor_training_approaching_update_receiver = (
    InstructorTrainingApproachingUpdateReceiver()
)
instructor_training_approaching_update_signal.connect(
    instructor_training_approaching_update_receiver
)


instructor_training_approaching_remove_receiver = (
    InstructorTrainingApproachingCancelReceiver()
)
instructor_training_approaching_remove_signal.connect(
    instructor_training_approaching_remove_receiver
)
