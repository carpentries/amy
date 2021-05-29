from consents.models import Consent, Term
from workshops.models import Person


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
