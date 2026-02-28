from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from src.consents.models import Term, TermOption, TermOptionChoices
from src.workshops.tests.base import TestBase


class ConsentTestBase(TestBase):
    def setUp(self) -> None:
        super()._setUpBadges()
        # Optional terms may not exist in the database.
        # Adding one in case.
        optional_term = Term.objects.create(
            content="I'm an optional term",
            slug="optional-test-term",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        TermOption.objects.create(term=optional_term, option_type=TermOptionChoices.AGREE)
        TermOption.objects.create(term=optional_term, option_type=TermOptionChoices.DECLINE)
        self.assert_required_terms()

    @contextmanager
    def terms_middleware(self) -> Generator[Any, None, Any]:
        """
        Remove workshops.action_required.PrivacyPolicy
        and replace it with consents.middleware.TermMiddleware
        """
        with self.modify_settings(
            MIDDLEWARE={
                "append": "src.consents.middleware.TermsMiddleware",
                "remove": ["src.workshops.action_required.PrivacyPolicy"],
            }
        ):
            yield

    def assert_required_terms(self) -> None:
        """
        Asserts that there are required Terms in the database.
        Terms are added via a migration.
        """
        self.assertTrue(Term.objects.filter(required_type=Term.PROFILE_REQUIRE_TYPE).active().exists())
