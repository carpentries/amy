import logging
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils import timezone
from typing_extensions import Unpack

from emails.controller import (
    EmailController,
    EmailControllerMissingRecipientsException,
    EmailControllerMissingTemplateException,
)
from emails.models import EmailTemplate, ScheduledEmail
from emails.signals import (
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
    messages_action_scheduled,
    messages_action_updated,
    messages_missing_recipients,
    messages_missing_template,
    messages_missing_template_link,
    one_month_before,
    person_from_request,
)
from workshops.models import Event, Task
from workshops.utils.feature_flags import feature_flag_enabled

logger = logging.getLogger("amy")


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
        template__signal=instructor_training_approaching_signal.signal_name,
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
    mapping = {
        StrategyEnum.CREATE: instructor_training_approaching_signal,
        StrategyEnum.UPDATE: instructor_training_approaching_update_signal,
        StrategyEnum.REMOVE: instructor_training_approaching_remove_signal,
    }
    if strategy not in mapping:
        return

    signal = mapping[strategy]

    logger.debug(f"Sending signal for {event} as result of strategy {strategy}")
    signal.send(
        sender=event,
        request=request,
        event=event,
        event_start_date=event.start,
    )


@receiver(instructor_training_approaching_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_training_approaching_receiver(
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
    signal = instructor_training_approaching_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=instructor_emails,
            generic_relation_obj=event,
            author=person_from_request(request),
        )
    except EmailControllerMissingRecipientsException:
        messages_missing_recipients(request, signal)
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)


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
    signal = instructor_training_approaching_signal.signal_name

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    try:
        scheduled_email = (
            ScheduledEmail.objects.select_for_update()
            .select_related("template")
            .get(
                generic_relation_content_type=ct,
                generic_relation_pk=event.pk,
                template__signal=signal,
                state="scheduled",
            )
        )

    except ScheduledEmail.DoesNotExist:
        logger.warning(
            f"Scheduled email for signal {signal} and event {event} does not exist."
        )
        return

    except ScheduledEmail.MultipleObjectsReturned:
        logger.warning(
            f"Too many scheduled emails for signal {signal} and event {event}."
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
        messages_missing_recipients(request, signal)
    except EmailControllerMissingTemplateException:
        # Note: this is not realistically possible because the scheduled email
        # is looked up using a specific template signal.
        messages_missing_template_link(request, scheduled_email)
    else:
        messages_action_updated(request, signal, scheduled_email)


@receiver(instructor_training_approaching_remove_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_training_approaching_remove_receiver(
    sender: Any, **kwargs: Unpack[InstructorTrainingApproachingKwargs]
) -> None:
    request = kwargs["request"]
    event = kwargs["event"]
    signal = instructor_training_approaching_remove_signal.signal_name

    ct = ContentType.objects.get_for_model(event)  # type: ignore
    scheduled_emails = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=event.pk,
        template__signal=signal,
        state="scheduled",
    ).select_for_update()

    for scheduled_email in scheduled_emails:
        scheduled_email = EmailController.cancel_email(
            scheduled_email=scheduled_email,
            author=person_from_request(request),
        )
        messages_action_cancelled(request, signal, scheduled_email)
