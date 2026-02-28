from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from src.consents.models import Consent, Term
from src.workshops.models import Person
from src.workshops.signals import person_archived_signal


@receiver(post_save, sender=Person)
def create_unset_consents_on_user_create(sender: Any, instance: Person, created: bool, **kwargs: Any) -> None:
    if created:
        Consent.objects.bulk_create(
            Consent(
                person=instance,
                term=term,
                term_option=None,
                archived_at=term.archived_at,
            )
            for term in Term.objects.all()
        )


@receiver(post_save, sender=Term)
def create_unset_consents_on_term_create(sender: Any, instance: Term, created: bool, **kwargs: Any) -> None:
    if created:
        Consent.objects.bulk_create(
            Consent(
                person=person,
                term=instance,
                term_option=None,
                archived_at=instance.archived_at,
            )
            for person in Person.objects.all()
        )


@receiver(person_archived_signal, sender=Person)
def unset_consents_on_person_archive(sender: Any, **kwargs: Any) -> None:
    person = kwargs["person"]
    Consent.archive_all_for_person(person=person)
