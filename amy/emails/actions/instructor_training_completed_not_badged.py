from datetime import datetime
import logging

from django.http import HttpRequest
from typing_extensions import Unpack

from emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from emails.signals import (
    Signal,
    instructor_training_completed_not_badged_remove_signal,
    instructor_training_completed_not_badged_signal,
    instructor_training_completed_not_badged_update_signal,
)
from emails.types import (
    InstructorTrainingCompletedNotBadgedContext,
    InstructorTrainingCompletedNotBadgedKwargs,
    StrategyEnum,
)
from emails.utils import two_months_after
from workshops.models import Award, Person

from .instructor_training_approaching import EmailStrategyException

logger = logging.getLogger("amy")


def instructor_training_completed_not_badged_strategy(
    person: Person,
) -> StrategyEnum:
    logger.info(f"Running InstructorTrainingCompletedNotBadged strategy for {person}")

    person_annotated = (
        Person.objects.annotate_with_instructor_eligibility().get(  # type: ignore
            pk=person.pk
        )
    )

    has_instructor_role = Award.objects.filter(
        role__name="instructor", person=person
    ).exists()

    all_requirements_passed = (
        person_annotated.passed_training
        and person_annotated.passed_get_involved
        and person_annotated.passed_welcome
        and person_annotated.passed_demo
    )

    if has_instructor_role or all_requirements_passed:
        result = StrategyEnum.REMOVE
    elif person_annotated.passed_training and not all_requirements_passed:
        result = StrategyEnum.CREATE
    elif (
        person_annotated.passed_training
        or person_annotated.passed_get_involved
        or person_annotated.passed_welcome
        or person_annotated.passed_demo
    ):
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"InstructorTrainingCompletedNotBadged strategy {result = }")
    return result


def run_instructor_training_completed_not_badged_strategy(
    strategy: StrategyEnum, request: HttpRequest, person: Person
) -> None:
    mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_training_completed_not_badged_signal,
        StrategyEnum.UPDATE: instructor_training_completed_not_badged_update_signal,
        StrategyEnum.REMOVE: instructor_training_completed_not_badged_remove_signal,
        StrategyEnum.NOOP: None,
    }
    if strategy not in mapping:
        raise EmailStrategyException(f"Unknown strategy {strategy}")

    signal = mapping[strategy]

    if not signal:
        logger.debug(f"Strategy {strategy} for {person} is a no-op")
        return

    logger.debug(f"Sending signal for {person} as result of strategy {strategy}")
    signal.send(
        sender=person,
        request=request,
        person=person,
    )


class InstructorTrainingCompletedNotBadgedReceiver(BaseAction):
    signal = instructor_training_completed_not_badged_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> datetime:
        training_completed_date = kwargs["training_completed_date"]
        return two_months_after(training_completed_date)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> InstructorTrainingCompletedNotBadgedContext:
        person = kwargs["person"]
        return {
            "person": person,
        }

    def get_generic_relation_object(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> Person:
        return context["person"]

    def get_recipients(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []


class InstructorTrainingCompletedNotBadgedUpdateReceiver(BaseActionUpdate):
    signal = instructor_training_completed_not_badged_update_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> datetime:
        training_completed_date = kwargs["training_completed_date"]
        return two_months_after(training_completed_date)

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> InstructorTrainingCompletedNotBadgedContext:
        person = kwargs["person"]
        return {
            "person": person,
        }

    def get_generic_relation_object(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> Person:
        return context["person"]

    def get_recipients(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []


class InstructorTrainingCompletedNotBadgedCancelReceiver(BaseActionCancel):
    signal = instructor_training_completed_not_badged_remove_signal.signal_name

    def get_context(
        self, **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs]
    ) -> InstructorTrainingCompletedNotBadgedContext:
        person = kwargs["person"]
        return {
            "person": person,
        }

    def get_generic_relation_object(
        self,
        context: InstructorTrainingCompletedNotBadgedContext,
        **kwargs: Unpack[InstructorTrainingCompletedNotBadgedKwargs],
    ) -> Person:
        return context["person"]


# -----------------------------------------------------------------------------
# Receivers

instructor_training_completed_not_badged_receiver = (
    InstructorTrainingCompletedNotBadgedReceiver()
)
instructor_training_completed_not_badged_signal.connect(
    instructor_training_completed_not_badged_receiver
)


instructor_training_completed_not_badged_update_receiver = (
    InstructorTrainingCompletedNotBadgedUpdateReceiver()
)
instructor_training_completed_not_badged_update_signal.connect(
    instructor_training_completed_not_badged_update_receiver
)


instructor_training_completed_not_badged_remove_receiver = (
    InstructorTrainingCompletedNotBadgedCancelReceiver()
)
instructor_training_completed_not_badged_remove_signal.connect(
    instructor_training_completed_not_badged_remove_receiver
)
