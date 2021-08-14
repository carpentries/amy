from datetime import timedelta

from django.test import TestCase

from autoemails.actions import NewConsentRequiredAction
from autoemails.models import EmailTemplate, Trigger
from consents.models import Term


class TestNewConsentRequiredAction(TestCase):
    def setUp(self):
        self.user_email = "admin@admin.com"
        self.action = NewConsentRequiredAction(
            trigger=Trigger(action="test-action", template=EmailTemplate()),
            objects={"person_email": self.user_email},
        )

    def test_launched_at(self):
        self.assertEqual(self.action.get_launch_at(), timedelta(hours=1))

    def test_recipients(self):
        """
        Test recipients and all_recipients methods that depend on one another
        """
        # Action with email given
        self.assertEqual(self.action.recipients(), (self.user_email,))
        self.assertEqual(self.action.all_recipients(), self.user_email)

        # Action with no email given
        action = NewConsentRequiredAction(trigger=self.action.trigger)
        self.assertIsNone(action.recipients())
        self.assertEqual(action.all_recipients(), "")

    def test_check(self):
        """
        Check method should return True for required consents and false otherwise.
        """
        required_term = Term(
            slug="test-required-term",
            content="required content",
            required_type=Term.PROFILE_REQUIRE_TYPE,
        )
        optional_term = Term(
            slug="test-optional-term",
            content="optional content",
            required_type=Term.OPTIONAL_REQUIRE_TYPE,
        )
        self.assertTrue(NewConsentRequiredAction.check(required_term))
        self.assertFalse(NewConsentRequiredAction.check(optional_term))
