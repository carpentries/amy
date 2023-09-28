from typing import Any

from django.dispatch import receiver
from typing_extensions import Unpack

from emails.controller import EmailController, EmailControllerMissingRecipientsException
from emails.models import EmailTemplate
from emails.signals import persons_merged_signal
from emails.types import PersonsMergedContext, PersonsMergedKwargs
from emails.utils import (
    immediate_action,
    messages_action_scheduled,
    messages_missing_recipients,
    messages_missing_template,
    person_from_request,
)
from workshops.models import Person
from workshops.utils.feature_flags import feature_flag_enabled


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
            to_header=[person.email] if person.email else [],
            generic_relation_obj=person,
            author=person_from_request(request),
        )
    except EmailControllerMissingRecipientsException:
        messages_missing_recipients(request, signal)
    except EmailTemplate.DoesNotExist:
        messages_missing_template(request, signal)
    else:
        messages_action_scheduled(request, signal, scheduled_email)
