from consents.models import Term, TermOption
from django.test.testcases import TestCase
from django.utils import timezone
from workshops.models import Person

from consents.util import person_has_consented_to_required_terms
from consents.tests.helpers import reconsent


class TestActiveTermConsentsForm(TestCase):
    def test_person_has_consented_to_required_terms(self) -> None:
        # required term
        required_term = Term.objects.create(
            content="required_term",
            slug="required_term",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        required_term_option = TermOption.objects.create(
            term=required_term, option_type=TermOption.AGREE
        )
        # optional Term
        Term.objects.create(
            content="not_required_term",
            slug="not_required_term",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        TermOption.objects.create(term=required_term, option_type=TermOption.AGREE)
        # archived required term
        Term.objects.create(
            content="archived_term",
            slug="archived_term",
            archived_at=timezone.now(),
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        TermOption.objects.create(
            term=required_term, option_type=TermOption.AGREE, archived_at=timezone.now()
        )
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        self.assertEqual(person_has_consented_to_required_terms(person), False)
        # Consent created for the required term; should return True
        reconsent(person=person, term=required_term, term_option=required_term_option)
        self.assertEqual(person_has_consented_to_required_terms(person), True)
