from typing import Any

from django.dispatch import receiver
from typing_extensions import Unpack

from emails.controller import EmailController, EmailControllerException
from emails.models import EmailTemplate
from emails.signals import admin_signs_instructor_up_for_workshop_signal
from emails.types import AdminSignsInstructorUpContext, AdminSignsInstructorUpKwargs
from emails.utils import (
    immediate_action,
    messages_action_scheduled,
    messages_missing_recipients,
    messages_missing_template,
    person_from_request,
)
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person
from workshops.utils.feature_flags import feature_flag_enabled


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
            to_header=[person.email] if person.email else [],
            generic_relation_obj=instructor_recruitment_signup,
            author=person_from_request(request),
        )
    except EmailControllerException:
        messages_missing_recipients(request, signal)
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)
