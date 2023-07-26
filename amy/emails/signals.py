from enum import StrEnum
from typing import Any, Mapping

from django.dispatch import Signal as DjangoSignal

from emails.types import (
    AdminSignsInstructorUpContext,
    InstructorBadgeAwardedContext,
    InstructorConfirmedContext,
    InstructorDeclinedContext,
    InstructorSignupContext,
    PersonsMergedContext,
)


class SignalNameEnum(StrEnum):
    instructor_badge_awarded = "instructor_badge_awarded"
    instructor_confirmed_for_workshop = "instructor_confirmed_for_workshop"
    instructor_declined_from_workshop = "instructor_declined_from_workshop"
    instructor_signs_up_for_workshop = "instructor_signs_up_for_workshop"
    admin_signs_instructor_up_for_workshop = "admin_signs_instructor_up_for_workshop"
    persons_merged = "persons_merged"

    @staticmethod
    def choices() -> list[tuple[str, str]]:
        return [
            (signal_name.value, signal_name.value) for signal_name in SignalNameEnum
        ]


class Signal(DjangoSignal):
    signal_name: SignalNameEnum
    context_type: type[Mapping[str, Any]]

    def __init__(self, *args, **kwargs):
        self.signal_name = kwargs.pop("signal_name")
        self.context_type = kwargs.pop("context_type")
        super().__init__(*args, **kwargs)


# Scheduled to run immediately after action (so roughly up to 1 hour later).
instructor_badge_awarded_signal = Signal(
    signal_name=SignalNameEnum.instructor_badge_awarded,
    context_type=InstructorBadgeAwardedContext,
)
instructor_confirmed_for_workshop_signal = Signal(
    signal_name=SignalNameEnum.instructor_confirmed_for_workshop,
    context_type=InstructorConfirmedContext,
)
instructor_declined_from_workshop_signal = Signal(
    signal_name=SignalNameEnum.instructor_declined_from_workshop,
    context_type=InstructorDeclinedContext,
)
instructor_signs_up_for_workshop_signal = Signal(
    signal_name=SignalNameEnum.instructor_signs_up_for_workshop,
    context_type=InstructorSignupContext,
)
admin_signs_instructor_up_for_workshop_signal = Signal(
    signal_name=SignalNameEnum.admin_signs_instructor_up_for_workshop,
    context_type=AdminSignsInstructorUpContext,
)
persons_merged_signal = Signal(
    signal_name=SignalNameEnum.persons_merged,
    context_type=PersonsMergedContext,
)

ALL_SIGNALS = [
    instructor_badge_awarded_signal,
    instructor_confirmed_for_workshop_signal,
    instructor_declined_from_workshop_signal,
    instructor_signs_up_for_workshop_signal,
    admin_signs_instructor_up_for_workshop_signal,
    persons_merged_signal,
]
