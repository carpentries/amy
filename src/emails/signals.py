from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from django.dispatch import Signal as DjangoSignal

from src.emails.types import (
    AdminSignsInstructorUpContext,
    AskForWebsiteContext,
    HostInstructorsIntroductionContext,
    InstructorBadgeAwardedContext,
    InstructorConfirmedContext,
    InstructorDeclinedContext,
    InstructorSignupContext,
    InstructorTaskCreatedForWorkshopContext,
    InstructorTrainingApproachingContext,
    InstructorTrainingCompletedNotBadgedContext,
    MembershipQuarterlyContext,
    NewMembershipOnboardingContext,
    NewSelfOrganisedWorkshopContext,
    PersonsMergedContext,
    PostWorkshop7DaysContext,
    RecruitHelpersContext,
)


class SignalNameEnum(StrEnum):
    instructor_badge_awarded = "instructor_badge_awarded"
    instructor_confirmed_for_workshop = "instructor_confirmed_for_workshop"
    instructor_declined_from_workshop = "instructor_declined_from_workshop"
    instructor_signs_up_for_workshop = "instructor_signs_up_for_workshop"
    admin_signs_instructor_up_for_workshop = "admin_signs_instructor_up_for_workshop"
    persons_merged = "persons_merged"
    instructor_task_created_for_workshop = "instructor_task_created_for_workshop"
    instructor_training_approaching = "instructor_training_approaching"
    instructor_training_completed_not_badged = "instructor_training_completed_not_badged"
    new_membership_onboarding = "new_membership_onboarding"
    host_instructors_introduction = "host_instructors_introduction"
    recruit_helpers = "recruit_helpers"
    post_workshop_7days = "post_workshop_7days"
    new_self_organised_workshop = "new_self_organised_workshop"
    ask_for_website = "ask_for_website"
    membership_quarterly_3_months = "membership_quarterly_3_months"
    membership_quarterly_6_months = "membership_quarterly_6_months"
    membership_quarterly_9_months = "membership_quarterly_9_months"

    @staticmethod
    def choices() -> list[tuple[str, str]]:
        return [(signal_name.value, signal_name.value) for signal_name in SignalNameEnum]


class Signal(DjangoSignal):
    signal_name: SignalNameEnum
    context_type: type[Mapping[str, Any]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.signal_name = kwargs.pop("signal_name")
        self.context_type = kwargs.pop("context_type")
        super().__init__(*args, **kwargs)


def triple_signals(name: str, context_type: Any) -> tuple[Signal, Signal, Signal]:
    return (
        Signal(signal_name=name, context_type=context_type),
        Signal(signal_name=name, context_type=context_type),
        Signal(signal_name=name, context_type=context_type),
    )


# Scheduled to run immediately after action (so roughly up to 1 hour later).
INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME = "instructor_badge_awarded"
(
    instructor_badge_awarded_signal,
    instructor_badge_awarded_update_signal,
    instructor_badge_awarded_cancel_signal,
) = triple_signals(SignalNameEnum.instructor_badge_awarded, InstructorBadgeAwardedContext)
INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME = "instructor_confirmed_for_workshop"
(
    instructor_confirmed_for_workshop_signal,
    instructor_confirmed_for_workshop_update_signal,
    instructor_confirmed_for_workshop_cancel_signal,
) = triple_signals(
    SignalNameEnum.instructor_confirmed_for_workshop,
    InstructorConfirmedContext,
)
INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME = "instructor_declined_from_workshop"
(
    instructor_declined_from_workshop_signal,
    instructor_declined_from_workshop_update_signal,
    instructor_declined_from_workshop_cancel_signal,
) = triple_signals(
    SignalNameEnum.instructor_declined_from_workshop,
    InstructorDeclinedContext,
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
INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME = "instructor_task_created_for_workshop"
(
    instructor_task_created_for_workshop_signal,
    instructor_task_created_for_workshop_update_signal,
    instructor_task_created_for_workshop_cancel_signal,
) = triple_signals(
    SignalNameEnum.instructor_task_created_for_workshop,
    InstructorTaskCreatedForWorkshopContext,
)

# Runs 1 month before the event.
INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME = "instructor_training_approaching"
(
    instructor_training_approaching_signal,
    instructor_training_approaching_update_signal,
    instructor_training_approaching_cancel_signal,
) = triple_signals(INSTRUCTOR_TRAINING_APPROACHING_SIGNAL_NAME, InstructorTrainingApproachingContext)

# Runs 2 months after completing training.
INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME = "instructor_training_completed_not_badged"
(
    instructor_training_completed_not_badged_signal,
    instructor_training_completed_not_badged_update_signal,
    instructor_training_completed_not_badged_cancel_signal,
) = triple_signals(
    INSTRUCTOR_TRAINING_COMPLETED_NOT_BADGED_SIGNAL_NAME,
    InstructorTrainingCompletedNotBadgedContext,
)

NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME = "new_membership_onboarding"
(
    new_membership_onboarding_signal,
    new_membership_onboarding_update_signal,
    new_membership_onboarding_cancel_signal,
) = triple_signals(NEW_MEMBERSHIP_ONBOARDING_SIGNAL_NAME, NewMembershipOnboardingContext)

HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME = "host_instructors_introduction"
(
    host_instructors_introduction_signal,
    host_instructors_introduction_update_signal,
    host_instructors_introduction_cancel_signal,
) = triple_signals(HOST_INSTRUCTORS_INTRODUCTION_SIGNAL_NAME, HostInstructorsIntroductionContext)

RECRUIT_HELPERS_SIGNAL_NAME = "recruit_helpers"
(
    recruit_helpers_signal,
    recruit_helpers_update_signal,
    recruit_helpers_cancel_signal,
) = triple_signals(RECRUIT_HELPERS_SIGNAL_NAME, RecruitHelpersContext)

POST_WORKSHOP_7DAYS_SIGNAL_NAME = "post_workshop_7days"
(
    post_workshop_7days_signal,
    post_workshop_7days_update_signal,
    post_workshop_7days_cancel_signal,
) = triple_signals(POST_WORKSHOP_7DAYS_SIGNAL_NAME, PostWorkshop7DaysContext)

new_self_organised_workshop_signal = Signal(
    signal_name=SignalNameEnum.new_self_organised_workshop,
    context_type=NewSelfOrganisedWorkshopContext,
)

ASK_FOR_WEBSITE_SIGNAL_NAME = "ask_for_website"
(
    ask_for_website_signal,
    ask_for_website_update_signal,
    ask_for_website_cancel_signal,
) = triple_signals(ASK_FOR_WEBSITE_SIGNAL_NAME, AskForWebsiteContext)

MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME = "membership_quarterly_3_months"
(
    membership_quarterly_3_months_signal,
    membership_quarterly_3_months_update_signal,
    membership_quarterly_3_months_cancel_signal,
) = triple_signals(MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME, MembershipQuarterlyContext)

MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME = "membership_quarterly_6_months"
(
    membership_quarterly_6_months_signal,
    membership_quarterly_6_months_update_signal,
    membership_quarterly_6_months_cancel_signal,
) = triple_signals(MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME, MembershipQuarterlyContext)

MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME = "membership_quarterly_9_months"
(
    membership_quarterly_9_months_signal,
    membership_quarterly_9_months_update_signal,
    membership_quarterly_9_months_cancel_signal,
) = triple_signals(MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME, MembershipQuarterlyContext)

ALL_SIGNALS = [item for item in locals().values() if isinstance(item, Signal)]

# A regular Django signal used for chaining certificate creation after instructor badge action is scheduled.
instructor_badge_awarded_signal_sent = DjangoSignal()
