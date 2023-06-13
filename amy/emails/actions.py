from datetime import timedelta
from typing import Any, TypedDict

from django.dispatch import receiver
from django.utils import timezone

from emails.controller import EmailController
from emails.signals import persons_merged_signal
from workshops.models import Person


class PersonsMergedKwargs(TypedDict):
    person_a_id: int
    person_b_id: int
    selected_person_id: int


@receiver(persons_merged_signal)
def persons_merged_receiver(sender: Any, **kwargs: PersonsMergedKwargs) -> None:
    scheduled_at = timezone.now() + timedelta(hours=1)
    person = Person.objects.get(pk=kwargs["selected_person_id"])
    context = {
        "person": person,
    }
    scheduled_email = EmailController.schedule_email(  # noqa
        signal="persons_merged",
        context=context,
        scheduled_at=scheduled_at,
        to_header=[person.email],
        from_header="team@carpentries.org",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
    )
    # TODO: associate scheduled_email with person
