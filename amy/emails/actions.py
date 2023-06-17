from datetime import timedelta
from typing import Any, TypedDict

from django.contrib import messages
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils import timezone

from emails.controller import EmailController
from emails.models import EmailTemplate
from emails.signals import persons_merged_signal
from workshops.models import Person


class PersonsMergedKwargs(TypedDict):
    request: HttpRequest
    person_a_id: int
    person_b_id: int
    selected_person_id: int


@receiver(persons_merged_signal)
def persons_merged_receiver(sender: Any, **kwargs: PersonsMergedKwargs) -> None:
    request: HttpRequest = kwargs["request"]
    scheduled_at = timezone.now() + timedelta(hours=1)
    person = Person.objects.get(pk=kwargs["selected_person_id"])
    context = {
        "person": person,
    }
    signal = "persons_merged"
    try:
        scheduled_email = EmailController.schedule_email(  # noqa
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            from_header="team@carpentries.org",
            reply_to_header="",
            cc_header=[],
            bcc_header=[],
        )
    except EmailTemplate.DoesNotExist:
        messages.warning(
            request,
            f"Action was not scheduled due to missing template for signal {signal}.",
        )
    # TODO: associate scheduled_email with person
