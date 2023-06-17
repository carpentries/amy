from datetime import timedelta
from typing import Any, TypedDict

from django.contrib import messages
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils import timezone
from typing_extensions import Unpack

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
def persons_merged_receiver(sender: Any, **kwargs: Unpack[PersonsMergedKwargs]) -> None:
    request = kwargs["request"]
    selected_person_id = kwargs["selected_person_id"]

    scheduled_at = timezone.now() + timedelta(hours=1)
    person = Person.objects.get(pk=selected_person_id)
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
        )
    except EmailTemplate.DoesNotExist:
        messages.warning(
            request,
            f"Action was not scheduled due to missing template for signal {signal}.",
        )
    else:
        messages.info(
            request,
            f"Action was scheduled: {scheduled_email.get_absolute_url()}.",
        )
    # TODO: associate scheduled_email with person
