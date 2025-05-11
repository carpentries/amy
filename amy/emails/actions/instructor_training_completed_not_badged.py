from datetime import date, datetime, timedelta
import logging
from typing import Any, Unpack

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.actions.base_strategy import run_strategy
from emails.actions.exceptions import EmailStrategyException
from emails.models import ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
    Signal,
    instructor_training_completed_not_badged_cancel_signal,
    instructor_training_completed_not_badged_signal,
    instructor_training_completed_not_badged_update_signal,
)
from emails.types import (
    InstructorTrainingCompletedNotBadgedContext,
    InstructorTrainingCompletedNotBadgedKwargs,
    StrategyEnum,
)
from emails.utils import (
    api_model_url,
    log_condition_elements,
    scalar_value_url,
    two_months_after,
)
from workshops.models import Award, Person, TrainingProgress, TrainingRequirement

logger = logging.getLogger("amy")


class TrainingCompletionDateException(Exception):
    pass


def find_training_completion_date(person: Person) -> date:
    """Given a person, find their passed training and related event.
    Return event end date."""
    training = TrainingProgress.objects.get(trainee=person, state="p", requirement__name="Training")
    event = training.event
    if not event:
        raise TrainingCompletionDateException("Training progress doesn't have an event.")

    training_completed_date = event.end
    if not training_completed_date:
        raise TrainingCompletionDateException("Training progress event doesn't have an end date.")

    return training_completed_date


def instructor_training_completed_not_badged_strategy(person: Person) -> StrategyEnum:
    logger.info(f"Running InstructorTrainingCompletedNotBadged strategy for {person}")

    person_annotated = Person.objects.annotate_with_instructor_eligibility().get(pk=person.pk)

    all_requirements_passed = bool(person_annotated.instructor_eligible)

    instructor_badge_not_awarded = not Award.objects.filter(person=person, badge__name="instructor").exists()

    ct = ContentType.objects.get_for_model(person)
    email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=person.pk,
        template__signal=INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
        state=ScheduledEmailStatus.SCHEDULED,
    ).exists()
    email_running_or_succeeded = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=person.pk,
        template__signal=INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
        state__in=[
            ScheduledEmailStatus.LOCKED,
            ScheduledEmailStatus.RUNNING,
            ScheduledEmailStatus.SUCCEEDED,
        ],
    ).exists()

    log_condition_elements(
        **{
            "person_annotated.passed_training": person_annotated.passed_training,
            "all_requirements_passed": all_requirements_passed,
            "instructor_badge_not_awarded": instructor_badge_not_awarded,
        }
    )

    email_should_exist = (
        bool(person_annotated.passed_training) and not all_requirements_passed and instructor_badge_not_awarded
    )

    # Prevents running sending multiple emails.
    if email_running_or_succeeded:
        result = StrategyEnum.NOOP
    elif not email_scheduled and email_should_exist:
        result = StrategyEnum.CREATE
    elif email_scheduled and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif email_scheduled and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"InstructorTrainingCompletedNotBadged strategy {result=}")
    return result


def run_instructor_training_completed_not_badged_strategy(
    strategy: StrategyEnum,
    request: HttpRequest,
    person: Person,
    training_completed_date: date | None,
    **kwargs: Any,
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_training_completed_not_badged_signal,
        StrategyEnum.UPDATE: instructor_training_completed_not_badged_update_signal,
        StrategyEnum.CANCEL: instructor_training_completed_not_badged_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    if not training_completed_date:
        try:
            training_completed_date = find_training_completion_date(person)
        except TrainingProgress.MultipleObjectsReturned as exc:
            raise EmailStrategyException(
                "Unable to determine training completion date. Person has multiple passed training progresses."
            ) from exc
        except TrainingProgress.DoesNotExist as exc:
            raise EmailStrategyException(
                "Unable to determine training completion date. Person doesn't have a passed training progress."
            ) from exc
        except TrainingCompletionDateException as exc:
            raise EmailStrategyException(
                "Unable to determine training completion date. Probably the person has "
                "training progress not linked to an event, or the event doesn't have "
                "an end date."
            ) from exc

    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=person,
        person=person,
        training_completed_date=training_completed_date,
        **kwargs,
    )


def get_scheduled_at(
    **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
) -> datetime:
    training_completed_date = kwargs["training_completed_date"]
    return two_months_after(training_completed_date)


def get_context(
    **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
) -> InstructorTrainingCompletedNotBadgedContext:
    person = kwargs["person"]
    passed_requirements = list(TrainingProgress.objects.filter(trainee=person, state="p"))
    not_passed_requirements = list(TrainingProgress.objects.filter(trainee=person).exclude(state="p"))
    not_graded_requirements = list(
        TrainingRequirement.objects.filter(name__in=["Training", "Get Involved", "Welcome Session", "Demo"]).exclude(
            trainingprogress__trainee=person
        )
    )
    training_completed_date = kwargs["training_completed_date"]

    # Certification deadline is defined as training completion date + 3 months
    # https://github.com/carpentries/amy/issues/2786
    certification_deadline = training_completed_date + timedelta(days=3 * 30)

    return {
        "person": person,
        "passed_requirements": passed_requirements,
        "not_passed_requirements": not_passed_requirements,
        "not_graded_requirements": not_graded_requirements,
        "training_completed_date": training_completed_date,
        "certification_deadline": certification_deadline,
    }


def get_context_json(
    context: InstructorTrainingCompletedNotBadgedContext,
) -> ContextModel:
    person = context["person"]
    return ContextModel(
        {
            "person": api_model_url("person", person.pk),
            "passed_requirements": [
                api_model_url("trainingprogress", progress.pk) for progress in context["passed_requirements"]
            ],
            "not_passed_requirements": [
                api_model_url("trainingprogress", progress.pk) for progress in context["not_passed_requirements"]
            ],
            "not_graded_requirements": [
                api_model_url("trainingrequirement", requirement.pk)
                for requirement in context["not_graded_requirements"]
            ],
            "training_completed_date": scalar_value_url("date", context["training_completed_date"].isoformat()),
            "certification_deadline": scalar_value_url("date", context["certification_deadline"].isoformat()),
        },
    )


def get_generic_relation_object(
    context: InstructorTrainingCompletedNotBadgedContext,
    **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
) -> Person:
    return context["person"]


def get_recipients(
    context: InstructorTrainingCompletedNotBadgedContext,
    **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorTrainingCompletedNotBadgedContext,
    **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", context["person"].pk),
                property="email",
            )
        ],
    )


class InstructorTrainingCompletedNotBadgedReceiver(BaseAction):
    signal = instructor_training_completed_not_badged_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> InstructorTrainingCompletedNotBadgedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTrainingCompletedNotBadgedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorTrainingCompletedNotBadgedUpdateReceiver(BaseActionUpdate):
    signal = instructor_training_completed_not_badged_update_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> InstructorTrainingCompletedNotBadgedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTrainingCompletedNotBadgedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorTrainingCompletedNotBadgedCancelReceiver(BaseActionCancel):
    signal = instructor_training_completed_not_badged_cancel_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> InstructorTrainingCompletedNotBadgedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorTrainingCompletedNotBadgedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> Person:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


# -----------------------------------------------------------------------------
# Receivers

instructor_training_completed_not_badged_receiver = InstructorTrainingCompletedNotBadgedReceiver()
instructor_training_completed_not_badged_signal.connect(instructor_training_completed_not_badged_receiver)


instructor_training_completed_not_badged_update_receiver = InstructorTrainingCompletedNotBadgedUpdateReceiver()
instructor_training_completed_not_badged_update_signal.connect(instructor_training_completed_not_badged_update_receiver)


instructor_training_completed_not_badged_cancel_receiver = InstructorTrainingCompletedNotBadgedCancelReceiver()
instructor_training_completed_not_badged_cancel_signal.connect(instructor_training_completed_not_badged_cancel_receiver)
