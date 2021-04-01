from django.db.models.signals import post_save
from django.dispatch import receiver
from workshops.models import Person
from consents.models import Term, Consent


@receiver(post_save, sender=Person)
def create_unset_consents_on_user_create(
    sender, instance: Person, created: bool, **kwargs
):
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
def create_unset_consents_on_term_create(
    sender, instance: Term, created: bool, **kwargs
):
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
