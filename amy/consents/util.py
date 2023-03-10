import logging

from autoemails.actions import NewConsentRequiredAction
from autoemails.bulk_email import send_bulk_email
from autoemails.models import Trigger
from consents.models import Consent, Term, TermEnum, TermOptionChoices
from workshops.models import Person

logger = logging.getLogger("amy")


def person_has_consented_to_required_terms(person: Person) -> bool:
    """
    Check the Required terms in the database
    and return true if they have all been consented to.
    """
    required_term_ids = (
        Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE)
        .active()
        .values_list("id")
    )
    term_ids_user_consented_to = (
        Consent.objects.filter(
            person=person,
            term__in=required_term_ids,
            term_option__isnull=False,
        )
        .active()
        .values_list("term_id")
    )
    return set(required_term_ids) == set(term_ids_user_consented_to)


def send_consent_email(request, term: Term) -> None:
    """
    Sending consent emails individually to each user to avoid
    exposing email addresses.
    """
    emails = (
        Consent.objects.filter(term=term, term_option__isnull=True)
        .active()
        .values_list("person__email", flat=True)
    )
    triggers = Trigger.objects.filter(
        active=True,
        action="consent-required",
    )
    send_bulk_email(
        request=request,
        action_class=NewConsentRequiredAction,
        triggers=triggers,
        emails=emails,
        additional_context_objects={"term": term},
        object_=term,
    )


def reconsent_for_term_option_type(
    term_key: TermEnum,
    term_option_type: TermOptionChoices,
    person: Person,
) -> Consent:
    """Find term by its key and ensure new consent for this term and this person is
    saved."""
    term = Term.objects.get_by_key(term_key)
    logger.debug(f"Found Term {term_key}: {term=}")

    term_option = term.termoption_set.get(option_type=term_option_type)
    logger.debug(f"Found Term {term_key} option: {term_option=}")

    old_consent = Consent.objects.active().get(person=person, term=term)
    new_consent = Consent.reconsent(old_consent, term_option)
    logger.debug(f"Reconsented old consent for term {term_option}: {new_consent=}")
    return new_consent
