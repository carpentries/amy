from django.utils import timezone

from consents.models import Term, TermOption
from consents.tests.base import ConsentTestBase
from consents.util import person_has_consented_to_required_terms
from workshops.models import Person


class TestActiveTermConsentsForm(ConsentTestBase):
    def test_person_has_consented_to_required_terms(self) -> None:
        # required term
        required_terms = Term.objects.filter(
            required_type=Term.PROFILE_REQUIRE_TYPE
        ).active()
        self.assertNotEqual(len(required_terms), 0)
        # optional Term
        Term.objects.create(
            content="not_required_term",
            slug="not_required_term",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        # archived required term
        Term.objects.create(
            content="archived_term",
            slug="archived_term",
            archived_at=timezone.now(),
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        TermOption.objects.create(
            term=required_terms[0],
            option_type=TermOption.AGREE,
            archived_at=timezone.now(),
        )
        person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )
        self.assertEqual(person_has_consented_to_required_terms(person), False)
        # Consents created for the required terms; should return True
        self.person_agree_to_terms(person, required_terms)
        self.assertEqual(person_has_consented_to_required_terms(person), True)
