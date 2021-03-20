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
