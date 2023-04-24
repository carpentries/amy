from collections import defaultdict

from django.utils import timezone

from consents.models import Consent


def archive_least_recent_active_consents(object_a, object_b, base_obj):
    """
    There is a unique database constraint on consents that only allows
    (person, term) when archived_at is null.
    This method archives one of the two active terms so
    that the combine merge method will be successful.
    """
    consents = Consent.objects.filter(person__in=[object_a, object_b])
    # Identify and group the active consents by term id
    active_consents_by_term_id = defaultdict(list)
    for consent in consents:
        if consent.archived_at is None:
            active_consents_by_term_id[consent.term_id].append(consent)

    # archive least recent active consents
    consents_to_archive = []
    consents_to_recreate = []
    for term_consents in active_consents_by_term_id.values():
        if len(term_consents) < 2:
            continue
        consent_a, consent_b = term_consents[0], term_consents[1]
        if consent_a.created_at < consent_b.created_at:
            consents_to_archive.append(consent_a)
        elif consent_b.created_at < consent_a.created_at:
            consents_to_archive.append(consent_b)
        else:
            # If they were created at the same time rather than being
            # nondeterministic archive both and when the user logs in again
            # they can consent to the term once more.
            consents_to_archive.append(consent_a)
            consents_to_archive.append(consent_b)
            consents_to_recreate.append(
                Consent(
                    person=base_obj,
                    term=consent_a.term,
                    term_option=None,
                )
            )
    Consent.objects.filter(pk__in=[c.pk for c in consents_to_archive]).update(
        archived_at=timezone.now()
    )
    Consent.objects.bulk_create(consents_to_recreate)
