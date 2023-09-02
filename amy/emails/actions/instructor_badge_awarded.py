from typing import Any

from django.dispatch import receiver
from typing_extensions import Unpack

from emails.controller import EmailController, EmailControllerException
from emails.models import EmailTemplate
from emails.signals import instructor_badge_awarded_signal
from emails.types import InstructorBadgeAwardedContext, InstructorBadgeAwardedKwargs
from emails.utils import (
    immediate_action,
    messages_action_scheduled,
    messages_missing_recipients,
    messages_missing_template,
    person_from_request,
)
from workshops.models import Award, Person
from workshops.utils.feature_flags import feature_flag_enabled


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
            to_header=[person.email] if person.email else [],
            generic_relation_obj=award,
            author=person_from_request(request),
        )
    except EmailControllerException:
        messages_missing_recipients(request, signal)
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)
