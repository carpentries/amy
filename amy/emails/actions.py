import logging
from typing import Any

from django.dispatch import receiver
from typing_extensions import Unpack

from emails.controller import EmailController
from emails.models import EmailTemplate
from emails.signals import (
    admin_signs_instructor_up_for_workshop_signal,
    instructor_badge_awarded_signal,
    instructor_confirmed_for_workshop_signal,
    instructor_declined_from_workshop_signal,
    instructor_signs_up_for_workshop_signal,
    persons_merged_signal,
)
from emails.types import (
    AdminSignsInstructorUpContext,
    AdminSignsInstructorUpKwargs,
    InstructorBadgeAwardedContext,
    InstructorBadgeAwardedKwargs,
    InstructorConfirmedContext,
    InstructorConfirmedKwargs,
    InstructorDeclinedContext,
    InstructorDeclinedKwargs,
    InstructorSignupContext,
    InstructorSignupKwargs,
    PersonsMergedContext,
    PersonsMergedKwargs,
)
from emails.utils import (
    immediate_action,
    messages_action_scheduled,
    messages_missing_template,
    person_from_request,
)
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Award, Event, Person
from workshops.utils.feature_flags import feature_flag_enabled

logger = logging.getLogger("amy")


@receiver(instructor_badge_awarded_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_badge_awarded_receiver(
    sender: Any, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
) -> None:
    request = kwargs["request"]
    person_id = kwargs["person_id"]
    award_id = kwargs["award_id"]

    scheduled_at = immediate_action()
    person = Person.objects.get(pk=person_id)
    award = Award.objects.get(pk=award_id)
    context: InstructorBadgeAwardedContext = {
        "person": person,
        "award": award,
    }
    signal = instructor_badge_awarded_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=award,
            author=person_from_request(request),
        )
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)


@receiver(instructor_confirmed_for_workshop_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_confirmed_for_workshop_receiver(
    sender: Any, **kwargs: Unpack[InstructorConfirmedKwargs]
) -> None:
    request = kwargs["request"]
    person_id = kwargs["person_id"]
    event_id = kwargs["event_id"]
    instructor_recruitment_signup_id = kwargs["instructor_recruitment_signup_id"]

    scheduled_at = immediate_action()
    person = Person.objects.get(pk=person_id)
    event = Event.objects.get(pk=event_id)
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.get(
        pk=instructor_recruitment_signup_id
    )
    context: InstructorConfirmedContext = {
        "person": person,
        "event": event,
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }
    signal = instructor_confirmed_for_workshop_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=instructor_recruitment_signup,
            author=person_from_request(request),
        )
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)


@receiver(instructor_declined_from_workshop_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_declined_from_workshop_receiver(
    sender: Any, **kwargs: Unpack[InstructorDeclinedKwargs]
) -> None:
    request = kwargs["request"]
    person_id = kwargs["person_id"]
    event_id = kwargs["event_id"]
    instructor_recruitment_signup_id = kwargs["instructor_recruitment_signup_id"]

    scheduled_at = immediate_action()
    person = Person.objects.get(pk=person_id)
    event = Event.objects.get(pk=event_id)
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.get(
        pk=instructor_recruitment_signup_id
    )
    context: InstructorDeclinedContext = {
        "person": person,
        "event": event,
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }
    signal = instructor_declined_from_workshop_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=instructor_recruitment_signup,
            author=person_from_request(request),
        )
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)


@receiver(instructor_signs_up_for_workshop_signal)
@feature_flag_enabled("EMAIL_MODULE")
def instructor_signs_up_for_workshop_receiver(
    sender: Any, **kwargs: Unpack[InstructorSignupKwargs]
) -> None:
    request = kwargs["request"]
    person_id = kwargs["person_id"]
    event_id = kwargs["event_id"]
    instructor_recruitment_signup_id = kwargs["instructor_recruitment_signup_id"]

    scheduled_at = immediate_action()
    person = Person.objects.get(pk=person_id)
    event = Event.objects.get(pk=event_id)
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.get(
        pk=instructor_recruitment_signup_id
    )
    context: InstructorSignupContext = {
        "person": person,
        "event": event,
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }
    signal = instructor_signs_up_for_workshop_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=instructor_recruitment_signup,
            author=person_from_request(request),
        )
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)


@receiver(admin_signs_instructor_up_for_workshop_signal)
@feature_flag_enabled("EMAIL_MODULE")
def admin_signs_instructor_up_for_workshop_receiver(
    sender: Any, **kwargs: Unpack[AdminSignsInstructorUpKwargs]
) -> None:
    request = kwargs["request"]
    person_id = kwargs["person_id"]
    event_id = kwargs["event_id"]
    instructor_recruitment_signup_id = kwargs["instructor_recruitment_signup_id"]

    scheduled_at = immediate_action()
    person = Person.objects.get(pk=person_id)
    event = Event.objects.get(pk=event_id)
    instructor_recruitment_signup = InstructorRecruitmentSignup.objects.get(
        pk=instructor_recruitment_signup_id
    )
    context: AdminSignsInstructorUpContext = {
        "person": person,
        "event": event,
        "instructor_recruitment_signup": instructor_recruitment_signup,
    }
    signal = admin_signs_instructor_up_for_workshop_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=instructor_recruitment_signup,
            author=person_from_request(request),
        )
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)


@receiver(persons_merged_signal)
@feature_flag_enabled("EMAIL_MODULE")
def persons_merged_receiver(sender: Any, **kwargs: Unpack[PersonsMergedKwargs]) -> None:
    request = kwargs["request"]
    selected_person_id = kwargs["selected_person_id"]

    scheduled_at = immediate_action()
    person = Person.objects.get(pk=selected_person_id)
    context: PersonsMergedContext = {
        "person": person,
    }
    signal = persons_merged_signal.signal_name
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=person,
            author=person_from_request(request),
        )
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)
