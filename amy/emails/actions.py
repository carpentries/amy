from datetime import timedelta
import logging
from typing import Any, TypedDict

from django.conf import settings
from django.contrib import messages
from django.dispatch import receiver
from django.http import HttpRequest
from django.utils import timezone
from typing_extensions import Unpack

from emails.controller import EmailController
from emails.models import EmailTemplate
from emails.signals import persons_merged_signal
from workshops.models import Person

logger = logging.getLogger("amy")


class PersonsMergedKwargs(TypedDict):
    request: HttpRequest
    person_a_id: int
    person_b_id: int
    selected_person_id: int


def check_feature_flag() -> bool:
    """Receivers will be connected no matter if EMAIL_MODULE_ENABLED is set or not.
    This function helps check if the receiver should exit early when the feature flag
    is disabled."""
    return settings.EMAIL_MODULE_ENABLED is True


@receiver(persons_merged_signal)
def persons_merged_receiver(sender: Any, **kwargs: Unpack[PersonsMergedKwargs]) -> None:
    if not check_feature_flag():
        logger.debug("EMAIL_MODULE_ENABLED not set, skipping persons_merged_receiver")
        return

    request = kwargs["request"]
    selected_person_id = kwargs["selected_person_id"]

    scheduled_at = timezone.now() + timedelta(hours=1)
    person = Person.objects.get(pk=selected_person_id)
    context = {
        "person": person,
    }
    signal = "persons_merged"
    try:
        scheduled_email = EmailController.schedule_email(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=person,
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
