from typing import Dict, Optional
from consents.models import Term, Consent
from workshops.models import Person


def consent_by_term(person: Person) -> Dict[Term, Optional[Consent]]:
    """
    Returns a dictionary of all terms with an optional Consent
    (null if the user has not consented, the consent object otherwise).
    """
    terms = Term.objects.active()
    consents = Consent.objects.filter(person=person).active()
    consent_by_term_id = {consent.term_id: consent for consent in consents}
    consent_by_term = {term: consent_by_term_id.get(term.id) for term in terms}
    return consent_by_term


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
