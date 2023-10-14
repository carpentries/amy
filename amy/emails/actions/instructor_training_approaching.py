from datetime import datetime
import logging
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils import timezone
from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.controller import (
    EmailController,
    EmailControllerMissingRecipientsException,
    EmailControllerMissingTemplateException,
)
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
from emails.utils import (
    messages_action_cancelled,
    messages_action_updated,
    messages_missing_recipients,
    messages_missing_template_link,
    one_month_before,
    person_from_request,
)
from workshops.models import Event, Task
from workshops.utils.feature_flags import feature_flag_enabled

logger = logging.getLogger("amy")


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

    def get_scheduled_at(self, **kwargs) -> datetime:
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
        self, context: InstructorTrainingApproachingContext, **kwargs
    ) -> Event:
        return context["event"]

    def get_recipients(
        self, context: InstructorTrainingApproachingContext, **kwargs
    ) -> list[str]:
        instructors = context["instructors"]
        return [instructor.email for instructor in instructors if instructor.email]


instructor_training_approaching_receiver = InstructorTrainingApproachingReceiver()
instructor_training_approaching_signal.connect(instructor_training_approaching_receiver)


@receiver(instructor_training_approaching_update_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_training_approaching_update_receiver(
    sender: Any, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
) -> None:
    request = kwargs["request"]
    event = kwargs["event"]
    event_start_date = kwargs["event_start_date"]
    instructors = [
        task.person
        for task in Task.objects.filter(event=event, role__name="instructor")
    ]
    instructor_emails = [
        instructor.email for instructor in instructors if instructor.email
    ]

    scheduled_at = one_month_before(event_start_date)
    context: InstructorTrainingApproachingContext = {
        "event": event,
        "instructors": instructors,
    }
    signal_name = INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    try:
        scheduled_email = (
            ScheduledEmail.objects.select_for_update()
            .select_related("template")
            .get(
                generic_relation_content_type=ct,
                generic_relation_pk=event.pk,
                template__signal=signal_name,
                state="scheduled",
            )
        )

    except ScheduledEmail.DoesNotExist:
        logger.warning(
            f"Scheduled email for signal {signal_name} and event {event} "
            "does not exist."
        )
        return

    except ScheduledEmail.MultipleObjectsReturned:
        logger.warning(
            f"Too many scheduled emails for signal {signal_name} and event {event}."
            " Can't update them."
        )
        return

    try:
        scheduled_email = EmailController.update_scheduled_email(
            scheduled_email=scheduled_email,
            context=context,
            scheduled_at=scheduled_at,
            to_header=instructor_emails,
            generic_relation_obj=event,
            author=person_from_request(request),
        )
    except EmailControllerMissingRecipientsException:
        messages_missing_recipients(request, signal_name)
    except EmailControllerMissingTemplateException:
        # Note: this is not realistically possible because the scheduled email
        # is looked up using a specific template signal.
        messages_missing_template_link(request, scheduled_email)
    else:
        messages_action_updated(request, signal_name, scheduled_email)


@receiver(instructor_training_approaching_remove_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_training_approaching_remove_receiver(
    sender: Any, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
) -> None:
    request = kwargs["request"]
    event = kwargs["event"]
    signal_name = INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    scheduled_emails = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=signal_name,
        state="scheduled",
    ).select_for_update()

    for scheduled_email in scheduled_emails:
        scheduled_email = EmailController.cancel_email(
            scheduled_email=scheduled_email,
            author=person_from_request(request),
        )
        messages_action_cancelled(request, signal_name, scheduled_email)
