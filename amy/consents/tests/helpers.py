from consents.models import Consent, Term, TermOption
from workshops.models import Person


def reconsent(person: Person, term: Term, term_option: TermOption) -> Consent:
    consent = Consent.objects.get(person=person, term=term, archived_at__isnull=True)
    consent.archive()
    return Consent.objects.create(term_option=term_option, term=term, person=person)
