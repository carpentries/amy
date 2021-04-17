from contextlib import contextmanager
from typing import Iterable

from consents.models import Consent, Term, TermOption
from workshops.models import Person
from workshops.tests.base import TestBase


class ConsentTestBase(TestBase):
    def setUp(self):
        super()._setUpAirports()
        super()._setUpBadges()
        # Optional terms may not exist in the database.
        # Adding one in case.
        optional_term = Term.objects.create(
            content="I'm an optional term",
            slug="optional-test-term",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        TermOption.objects.create(term=optional_term, option_type=TermOption.AGREE)
        TermOption.objects.create(term=optional_term, option_type=TermOption.DECLINE)
        self.assert_required_terms()

    @staticmethod
    def reconsent(person: Person, term: Term, term_option: TermOption) -> Consent:
        consent = Consent.objects.get(
            person=person, term=term, archived_at__isnull=True
        )
        consent.archive()
        return Consent.objects.create(term_option=term_option, term=term, person=person)

    def person_agree_to_terms(self, person: Person, terms: Iterable[Term]) -> None:
        for term in terms:
            self.reconsent(person=person, term_option=term.options[0], term=term)

    @contextmanager
    def terms_middleware(self) -> None:
        """
        Remove workshops.action_required.PrivacyPolicy
        and replace it with consents.middleware.TermMiddleware
        """
        with self.modify_settings(
            MIDDLEWARE={
                "append": "consents.middleware.TermsMiddleware",
                "remove": ["workshops.action_required.PrivacyPolicy"],
            }
        ):
            yield

    def assert_required_terms(self) -> None:
        """
        Asserts that there are required Terms in the database.
        Terms are added via a migration.
        """
        self.assertTrue(
            Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE)
            .active()
            .exists()
        )
