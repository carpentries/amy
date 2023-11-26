from enum import StrEnum
from typing import Any, Mapping

from django.dispatch import Signal as DjangoSignal

from emails.types import (
    AdminSignsInstructorUpContext,
    InstructorBadgeAwardedContext,
    InstructorConfirmedContext,
    InstructorDeclinedContext,
    InstructorSignupContext,
    InstructorTrainingApproachingContext,
    InstructorTrainingCompletedNotBadgedContext,
    NewMembershipOnboardingContext,
    PersonsMergedContext,
)


class SignalNameEnum(StrEnum):
    instructor_badge_awarded = "instructor_badge_awarded"
    instructor_confirmed_for_workshop = "instructor_confirmed_for_workshop"
    instructor_declined_from_workshop = "instructor_declined_from_workshop"
    instructor_signs_up_for_workshop = "instructor_signs_up_for_workshop"
    admin_signs_instructor_up_for_workshop = "admin_signs_instructor_up_for_workshop"
    persons_merged = "persons_merged"
    instructor_training_approaching = "instructor_training_approaching"
    instructor_training_completed_not_badged = (
        "instructor_training_completed_not_badged"
    )
    new_membership_onboarding = "new_membership"

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

# Runs 1 month before the event.
INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME = "instructor_training_approaching"
instructor_training_approaching_signal = Signal(
    signal_name=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
    context_type=InstructorTrainingApproachingContext,
)
# Emitted when conditions for the previous signal may have changed and
# the email should be re-calculated.
instructor_training_approaching_update_signal = Signal(
    signal_name=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
    context_type=InstructorTrainingApproachingContext,
)
# Emitted when conditions for the previous signal may have changed and
# the email should be cancelled.
instructor_training_approaching_remove_signal = Signal(
    signal_name=INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME,
    context_type=InstructorTrainingApproachingContext,
)

# Runs 2 months after completing training.
INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME = (
    "instructor_training_completed_not_badged"
)
instructor_training_completed_not_badged_signal = Signal(
    signal_name=INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
    context_type=InstructorTrainingCompletedNotBadgedContext,
)
# Emitted when conditions for the previous signal may have changed and
# the email should be re-calculated.
instructor_training_completed_not_badged_update_signal = Signal(
    signal_name=INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
    context_type=InstructorTrainingCompletedNotBadgedContext,
)
# Emitted when conditions for the previous signal may have changed and
# the email should be cancelled.
instructor_training_completed_not_badged_remove_signal = Signal(
    signal_name=INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
    context_type=InstructorTrainingCompletedNotBadgedContext,
)

NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME = "new_membership_onboarding"
new_membership_onboarding_signal = Signal(
    signal_name=NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
    context_type=NewMembershipOnboardingContext,
)
new_membership_onboarding_update_signal = Signal(
    signal_name=NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
    context_type=NewMembershipOnboardingContext,
)
new_membership_onboarding_remove_signal = Signal(
    signal_name=NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME,
    context_type=NewMembershipOnboardingContext,
)

ALL_SIGNALS = [item for item in locals().values() if isinstance(item, Signal)]
